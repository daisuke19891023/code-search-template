"""Semantic search tool using embeddings and a vector index."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from codeagent_lab.models import SemanticHit, SemanticParams, SemanticResult
from codeagent_lab.tools._path_filters import resolve_within_root
from codeagent_lab.tools.protocols import Tool

if TYPE_CHECKING:
    from codeagent_lab.embeddings.protocols import EmbeddingBackend
    from codeagent_lab.vectordb.protocols import VectorIndex


@dataclass
class _Document:
    """File content and relative path used for indexing."""

    path: Path
    text: str


class SemanticOpenAITool(Tool[SemanticParams, SemanticResult]):
    """Embed repository files, persist a vector index, and execute search."""

    name = "semantic.openai"
    Param = SemanticParams
    Result = SemanticResult

    max_file_bytes = 512_000
    _manifest_name = "manifest.json"

    def __init__(self, embedder: EmbeddingBackend, index: VectorIndex, index_root: str) -> None:
        """Initialise the semantic tool with dependencies."""
        self._embedder = embedder
        self._index = index
        self._index_root = Path(index_root)

    def run(self, params: SemanticParams) -> SemanticResult:
        """Embed the query and search against a persisted vector index."""
        start = time.perf_counter()
        root = Path(params.root)
        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {"error": "root-missing", "root": str(root)}
            return SemanticResult(ok=False, hits=[], latency_ms=latency_ms, meta=meta)

        index_dir = self._index_directory(root)
        index_meta: dict[str, Any] = {"path": str(index_dir)}
        doc_ids, built = self._ensure_index(root, index_dir)
        index_meta["built"] = built
        documents_indexed = len(doc_ids)

        query_vectors = self._embedder.embed([params.query])
        query_matrix = np.asarray(query_vectors, dtype="float32")

        hits: list[SemanticHit] = []
        if documents_indexed > 0 and params.topk > 0:
            topk = min(params.topk, documents_indexed)
            search_results = self._index.search(query_matrix, topk=topk)
            first_result = search_results[0] if search_results else []
            hits = [SemanticHit(path=doc_id, score=score) for doc_id, score in first_result]

        latency_ms = int((time.perf_counter() - start) * 1000)
        meta = {"index": index_meta, "documents": documents_indexed}
        return SemanticResult(hits=hits, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search using embeddings and a vector index."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    def _ensure_index(self, root: Path, index_dir: Path) -> tuple[list[str], bool]:
        """Load an existing index or build a new one for ``root``."""
        if self._can_load_index(index_dir):
            try:
                manifest = self._load_manifest(index_dir)
            except (OSError, ValueError, json.JSONDecodeError):
                # Fall back to rebuilding the index when persistence is invalid.
                self._remove_manifest(index_dir)
            else:
                if self._manifest_matches(manifest):
                    try:
                        self._index.load(str(index_dir))
                    except (OSError, ValueError, RuntimeError):
                        # Fall back to rebuilding the index when persisted data is corrupt.
                        self._remove_manifest(index_dir)
                    else:
                        documents = [str(doc) for doc in manifest.get("documents", [])]
                        return documents, False
        return self._build_index(root, index_dir)

    def _build_index(self, root: Path, index_dir: Path) -> tuple[list[str], bool]:
        """Embed files under ``root`` and persist the resulting index."""
        documents = self._collect_documents(root)
        if not documents:
            return [], False

        texts = [doc.text for doc in documents]
        doc_ids = [str(doc.path) for doc in documents]
        vectors = np.asarray(self._embedder.embed(texts), dtype="float32")
        self._index.build(vectors, doc_ids)

        index_dir.mkdir(parents=True, exist_ok=True)
        self._index.save(str(index_dir))
        self._save_manifest(index_dir, root, doc_ids)
        return doc_ids, True

    def _collect_documents(self, root: Path) -> list[_Document]:
        """Return text documents under ``root`` suitable for indexing."""
        documents: list[_Document] = []
        resolved_root = root.resolve()
        for path in sorted(root.rglob("*")):
            resolved = resolve_within_root(resolved_root, path)
            if resolved is None or not resolved.is_file():
                continue
            try:
                relative = resolved.relative_to(resolved_root)
            except ValueError:
                continue
            if self._is_hidden(relative):
                continue
            try:
                size = resolved.stat().st_size
            except OSError:
                continue
            if size > self.max_file_bytes:
                continue
            try:
                text = resolved.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "\x00" in text:
                continue
            documents.append(_Document(path=relative, text=text))
        return documents

    def _index_directory(self, root: Path) -> Path:
        """Return the directory where the index for ``root`` is stored."""
        digest = hashlib.sha1(str(root.resolve()).encode("utf-8"), usedforsecurity=False).hexdigest()
        return self._index_root / digest

    def _manifest_path(self, index_dir: Path) -> Path:
        """Return the path to the manifest file for ``index_dir``."""
        return index_dir / self._manifest_name

    def _can_load_index(self, index_dir: Path) -> bool:
        """Return ``True`` if a persisted index appears to exist."""
        manifest_path = self._manifest_path(index_dir)
        return index_dir.is_dir() and manifest_path.is_file()

    def _save_manifest(self, index_dir: Path, root: Path, documents: list[str]) -> None:
        """Persist index metadata describing the stored documents."""
        manifest = {
            "version": 1,
            "root": str(root.resolve()),
            "embedder": getattr(self._embedder, "name", "unknown"),
            "dimension": getattr(self._embedder, "dimension", 0),
            "documents": documents,
        }
        with self._manifest_path(index_dir).open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle)

    def _load_manifest(self, index_dir: Path) -> dict[str, Any]:
        """Load persisted index metadata."""
        with self._manifest_path(index_dir).open(encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("version") != 1:
            message = "unsupported manifest version"
            raise ValueError(message)
        documents = data.get("documents")
        if documents is None:
            message = "manifest missing documents list"
            raise ValueError(message)
        return data

    def _remove_manifest(self, index_dir: Path) -> None:
        """Best-effort removal of a stale manifest before rebuilding."""
        manifest_path = self._manifest_path(index_dir)
        try:
            manifest_path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return

    def _manifest_matches(self, manifest: dict[str, Any]) -> bool:
        """Return ``True`` if the manifest is compatible with the embedder/index."""
        embedder_name = getattr(self._embedder, "name", None)
        embedder_dim = getattr(self._embedder, "dimension", None)
        return (
            manifest.get("embedder") == embedder_name
            and manifest.get("dimension") == embedder_dim
        )

    @staticmethod
    def _relative_path(root: Path, path: Path) -> Path:
        """Return ``path`` relative to ``root`` with graceful fallback."""
        try:
            return path.relative_to(root)
        except ValueError:
            resolved_root = root.resolve()
            try:
                return path.relative_to(resolved_root)
            except ValueError:
                return path

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        """Return ``True`` if any path component is hidden."""
        return any(part.startswith(".") for part in path.parts if part not in {"", "."})
