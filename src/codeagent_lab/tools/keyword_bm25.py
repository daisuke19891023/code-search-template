"""BM25 keyword search over repository files."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from rank_bm25 import BM25Okapi

from codeagent_lab.models import KeywordHit, KeywordParams, KeywordResult
from codeagent_lab.tools._path_filters import resolve_within_root
from codeagent_lab.tools.protocols import Tool

if TYPE_CHECKING:
    import os
    from collections.abc import Callable


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_DEFAULT_INDEX_ROOT = Path(".labdata/indexes")
_MANIFEST_NAME = "manifest.json"
_MANIFEST_VERSION = 1


class _BM25Scorer(Protocol):
    """Subset of BM25 scorer functionality relied upon by the tool."""

    def get_scores(self, query: list[str]) -> list[float]:
        ...


@dataclass
class _Document:
    """Internal representation of a file considered for ranking."""

    path: Path
    tokens: list[str]


@dataclass
class _ProcessedCandidate:
    """Result of processing a single file candidate during indexing."""

    key: str
    entry: dict[str, object] | None
    tokens: list[str] | None
    changed: bool


class KeywordIndexManager:
    """Persist and reuse tokenised keyword documents for BM25 scoring."""

    def __init__(
        self,
        index_root: str | Path,
        *,
        max_file_bytes: int,
        tokenizer: Callable[[str], list[str]],
        token_pattern: str,
        manifest_name: str = _MANIFEST_NAME,
    ) -> None:
        """Initialise the index manager configuration."""
        self._index_root = Path(index_root)
        self._index_root.mkdir(parents=True, exist_ok=True)
        self._max_file_bytes = max_file_bytes
        self._tokenizer = tokenizer
        self._token_pattern = token_pattern
        self._manifest_name = manifest_name

    def ensure_documents(self, root: Path) -> tuple[list[_Document], bool]:
        """Return tokenised documents for ``root`` using cached state when available."""
        index_dir = self._index_directory(root)
        resolved_root = root.resolve()
        entries, manifest_reset = self._prepare_entries(index_dir, resolved_root)
        current_entries, updated_tokens, scan_changed = self._scan_root(
            root, resolved_root, index_dir, entries,
        )
        removal_changed = self._remove_missing(entries, current_entries, index_dir)
        documents, materialised_changed = self._materialise_documents(
            resolved_root, index_dir, current_entries, updated_tokens,
        )

        changed = manifest_reset or scan_changed or removal_changed or materialised_changed
        manifest_data: dict[str, object] = {
            "version": _MANIFEST_VERSION,
            "root": str(resolved_root),
            "config": self._config_signature(),
            "files": cast(object, current_entries),
        }
        self._write_manifest(index_dir, manifest_data)
        return documents, changed

    def _prepare_entries(
        self, index_dir: Path, resolved_root: Path,
    ) -> tuple[dict[str, dict[str, object]], bool]:
        manifest, entries = self._load_manifest(index_dir)
        if manifest is None:
            return entries, False
        if not self._manifest_matches(manifest, resolved_root):
            self._purge_index(index_dir, entries)
            return {}, True
        return entries, False

    def _scan_root(
        self,
        root: Path,
        resolved_root: Path,
        index_dir: Path,
        previous_entries: dict[str, dict[str, object]],
    ) -> tuple[dict[str, dict[str, object]], dict[str, list[str]], bool]:
        current_entries: dict[str, dict[str, object]] = {}
        updated_tokens: dict[str, list[str]] = {}
        changed = False

        for candidate in sorted(root.rglob("*")):
            result = self._process_candidate(candidate, resolved_root, previous_entries, index_dir)
            if result is None:
                continue
            changed = changed or result.changed
            if result.entry is None:
                continue
            current_entries[result.key] = result.entry
            if result.tokens is not None:
                updated_tokens[result.key] = result.tokens
        return current_entries, updated_tokens, changed

    def _process_candidate(
        self,
        candidate: Path,
        resolved_root: Path,
        previous_entries: dict[str, dict[str, object]],
        index_dir: Path,
    ) -> _ProcessedCandidate | None:
        metadata = self._resolve_candidate_metadata(candidate, resolved_root)
        if metadata is None:
            return None
        resolved, relative, stat_result = metadata

        key = relative.as_posix()
        existing = previous_entries.get(key)

        if stat_result.st_size > self._max_file_bytes:
            return self._handle_excluded(existing, index_dir, key)

        changed = False
        if self._can_reuse_existing(existing, stat_result, index_dir):
            entry_result = existing
            tokens_result = None
        else:
            entry_result, tokens_result, changed = self._tokenize_candidate(
                resolved, existing, index_dir, key, stat_result,
            )

        return _ProcessedCandidate(
            key=key,
            entry=entry_result,
            tokens=tokens_result,
            changed=changed,
        )

    def _resolve_candidate_metadata(
        self, candidate: Path, resolved_root: Path,
    ) -> tuple[Path, Path, os.stat_result] | None:
        resolved = resolve_within_root(resolved_root, candidate)
        if resolved is None or not resolved.is_file():
            return None
        try:
            relative = resolved.relative_to(resolved_root)
        except ValueError:
            return None
        if self._is_hidden(relative):
            return None
        try:
            stat_result = resolved.stat()
        except OSError:
            return None
        return resolved, relative, stat_result

    def _handle_excluded(
        self,
        existing: dict[str, object] | None,
        index_dir: Path,
        key: str,
    ) -> _ProcessedCandidate:
        changed = False
        if existing is not None:
            self._remove_tokens(index_dir, existing)
            changed = True
        return _ProcessedCandidate(key=key, entry=None, tokens=None, changed=changed)

    def _can_reuse_existing(
        self,
        existing: dict[str, object] | None,
        stat_result: os.stat_result,
        index_dir: Path,
    ) -> bool:
        if existing is None:
            return False
        entry_mtime = existing.get("mtime_ns")
        entry_size = existing.get("size")
        tokens_path = self._tokens_path(index_dir, existing)
        return (
            entry_mtime == stat_result.st_mtime_ns
            and entry_size == stat_result.st_size
            and tokens_path is not None
            and tokens_path.is_file()
        )

    def _tokenize_candidate(
        self,
        resolved: Path,
        existing: dict[str, object] | None,
        index_dir: Path,
        key: str,
        stat_result: os.stat_result,
    ) -> tuple[dict[str, object] | None, list[str] | None, bool]:
        tokens_info = self._tokenize_file(resolved)
        if tokens_info is None:
            changed = False
            if existing is not None:
                self._remove_tokens(index_dir, existing)
                changed = True
            return None, None, changed

        digest, tokens = tokens_info
        entry: dict[str, object] = {
            "path": key,
            "mtime_ns": stat_result.st_mtime_ns,
            "size": stat_result.st_size,
            "hash": digest,
            "tokens": self._write_tokens(index_dir, key, tokens),
        }
        return entry, tokens, True

    def _remove_missing(
        self,
        previous_entries: dict[str, dict[str, object]],
        current_entries: dict[str, dict[str, object]],
        index_dir: Path,
    ) -> bool:
        changed = False
        for key, entry in previous_entries.items():
            if key not in current_entries:
                self._remove_tokens(index_dir, entry)
                changed = True
        return changed

    def _materialise_documents(
        self,
        resolved_root: Path,
        index_dir: Path,
        entries: dict[str, dict[str, object]],
        updated_tokens: dict[str, list[str]],
    ) -> tuple[list[_Document], bool]:
        documents: list[_Document] = []
        changed = False
        for key in sorted(entries):
            entry = entries[key]
            tokens = updated_tokens.get(key)
            if tokens is None:
                tokens = self._read_tokens(index_dir, entry)
            if tokens is None:
                rebuilt = self._rebuild_entry_for_path(resolved_root, index_dir, key)
                if rebuilt is None:
                    self._remove_tokens(index_dir, entry)
                    entries.pop(key, None)
                    updated_tokens.pop(key, None)
                    changed = True
                    continue
                entry, tokens = rebuilt
                entries[key] = entry
                updated_tokens[key] = tokens
                changed = True
            documents.append(
                _Document(path=resolved_root / Path(key), tokens=list(tokens)),
            )
        return documents, changed

    def _rebuild_entry_for_path(
        self, resolved_root: Path, index_dir: Path, key: str,
    ) -> tuple[dict[str, object], list[str]] | None:
        file_path = resolved_root / Path(key)
        try:
            stat_result = file_path.stat()
        except OSError:
            return None
        if stat_result.st_size > self._max_file_bytes:
            return None
        tokens_info = self._tokenize_file(file_path)
        if tokens_info is None:
            return None
        digest, tokens = tokens_info
        entry: dict[str, object] = {
            "path": key,
            "mtime_ns": stat_result.st_mtime_ns,
            "size": stat_result.st_size,
            "hash": digest,
            "tokens": self._write_tokens(index_dir, key, tokens),
        }
        return entry, tokens

    def _index_directory(self, root: Path) -> Path:
        digest = hashlib.sha1(
            str(root.resolve()).encode("utf-8"), usedforsecurity=False,
        ).hexdigest()
        return self._index_root / digest / "keyword"

    def _write_manifest(self, index_dir: Path, manifest: dict[str, object]) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = index_dir / self._manifest_name
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle)

    def _load_manifest(
        self, index_dir: Path,
    ) -> tuple[dict[str, object] | None, dict[str, dict[str, object]]]:
        manifest_path = index_dir / self._manifest_name
        if not index_dir.is_dir() or not manifest_path.is_file():
            return None, {}
        try:
            with manifest_path.open(encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, json.JSONDecodeError, ValueError):
            return None, {}
        if manifest.get("version") != _MANIFEST_VERSION:
            return None, {}
        files = manifest.get("files")
        if not isinstance(files, dict):
            return None, {}
        files_dict = cast(dict[Any, Any], files)
        normalised: dict[str, dict[str, object]] = {}
        for key_obj, value_obj in files_dict.items():
            if not isinstance(key_obj, str) or not isinstance(value_obj, dict):
                continue
            nested = cast(dict[Any, Any], value_obj)
            entry: dict[str, object] = {}
            for sub_key, sub_value in nested.items():
                entry[str(sub_key)] = cast(object, sub_value)
            normalised[key_obj] = entry
        return manifest, normalised

    def _manifest_matches(self, manifest: dict[str, object], resolved_root: Path) -> bool:
        config = manifest.get("config")
        stored_root = manifest.get("root")
        return (
            isinstance(config, dict)
            and config == self._config_signature()
            and isinstance(stored_root, str)
            and stored_root == str(resolved_root)
        )

    def _config_signature(self) -> dict[str, object]:
        return {
            "max_file_bytes": self._max_file_bytes,
            "token_pattern": self._token_pattern,
        }

    def _tokenize_file(self, path: Path) -> tuple[str, list[str]] | None:
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if b"\x00" in raw:
            return None
        try:
            text = raw.decode("utf-8", errors="ignore")
        except UnicodeDecodeError:
            return None
        tokens = self._tokenizer(text)
        if not tokens:
            return None
        digest = hashlib.sha1(raw, usedforsecurity=False).hexdigest()
        return digest, tokens

    def _write_tokens(self, index_dir: Path, path_key: str, tokens: list[str]) -> str:
        digest = hashlib.sha1(path_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        tokens_dir = index_dir / "tokens"
        tokens_dir.mkdir(parents=True, exist_ok=True)
        tokens_path = tokens_dir / f"{digest}.json"
        with tokens_path.open("w", encoding="utf-8") as handle:
            json.dump(tokens, handle)
        return f"tokens/{digest}.json"

    def _read_tokens(self, index_dir: Path, entry: dict[str, object]) -> list[str] | None:
        tokens_path = self._tokens_path(index_dir, entry)
        if tokens_path is None or not tokens_path.is_file():
            return None
        try:
            with tokens_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, list):
            return None
        tokens_list = cast(list[Any], data)
        return [str(token) for token in tokens_list]

    @staticmethod
    def _tokens_path(index_dir: Path, entry: dict[str, object]) -> Path | None:
        tokens_rel = entry.get("tokens")
        if not isinstance(tokens_rel, str):
            return None
        candidate = index_dir / tokens_rel
        try:
            candidate.resolve().relative_to(index_dir.resolve())
        except (ValueError, OSError):
            return None
        return candidate

    @staticmethod
    def _remove_tokens(index_dir: Path, entry: dict[str, object]) -> None:
        tokens_path = KeywordIndexManager._tokens_path(index_dir, entry)
        if tokens_path is None:
            return
        try:
            tokens_path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return

    @staticmethod
    def _purge_index(index_dir: Path, entries: dict[str, dict[str, object]]) -> None:
        for entry in entries.values():
            KeywordIndexManager._remove_tokens(index_dir, entry)
        try:
            (index_dir / _MANIFEST_NAME).unlink()
        except FileNotFoundError:
            pass
        except OSError:
            return

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        return any(part.startswith(".") for part in path.parts if part not in {"", "."})


class KeywordBM25Tool(Tool[KeywordParams, KeywordResult]):
    """Rank repository files using BM25 scoring."""

    name = "keyword.bm25"
    Param = KeywordParams
    Result = KeywordResult

    default_max_file_bytes = 512_000

    def __init__(
        self,
        *,
        index_manager: KeywordIndexManager | None = None,
        index_root: str | Path | None = None,
        max_file_bytes: int | None = None,
    ) -> None:
        """Initialise the BM25 tool with optional persistence configuration."""
        self.max_file_bytes = max_file_bytes if max_file_bytes is not None else self.default_max_file_bytes
        if index_manager is not None:
            self._index_manager = index_manager
        else:
            root = Path(index_root) if index_root is not None else _DEFAULT_INDEX_ROOT
            self._index_manager = KeywordIndexManager(
                index_root=root,
                max_file_bytes=self.max_file_bytes,
                tokenizer=self._tokenize,
                token_pattern=_TOKEN_PATTERN.pattern,
            )

    def run(self, params: KeywordParams) -> KeywordResult:
        """Execute BM25 ranking over files under ``params.root``."""
        start = time.perf_counter()
        root = Path(params.root)
        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            return KeywordResult(
                ok=False,
                hits=[],
                latency_ms=latency_ms,
                meta={"error": "root-missing", "root": str(root)},
            )

        documents, _ = self._index_manager.ensure_documents(root)
        query_tokens = self._tokenize(params.query)

        if not documents or not query_tokens:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return KeywordResult(
                hits=[],
                latency_ms=latency_ms,
                meta={"documents": len(documents), "query_tokens": len(query_tokens)},
            )

        bm25 = BM25Okapi([doc.tokens for doc in documents])
        scorer = cast("_BM25Scorer", bm25)
        raw_scores = scorer.get_scores(query_tokens)
        scores = [float(score) for score in raw_scores]

        topk = max(0, min(params.topk, len(scores)))
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:topk]

        hits = [
            KeywordHit(path=str(self._relative_path(root, documents[idx].path)), score=scores[idx])
            for idx in ranked_indices
        ]

        latency_ms = int((time.perf_counter() - start) * 1000)
        return KeywordResult(
            hits=hits,
            latency_ms=latency_ms,
            meta={"documents": len(documents), "query_tokens": len(query_tokens)},
        )

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Rank files using BM25 keyword scoring."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize ``text`` into lower-case alphanumeric tokens."""
        return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]

    @property
    def index_manager(self) -> KeywordIndexManager:
        """Return the index manager responsible for token persistence."""
        return self._index_manager

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
