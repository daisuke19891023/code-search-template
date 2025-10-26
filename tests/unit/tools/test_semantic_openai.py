"""Tests for the semantic search tool."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from codeagent_lab.models import SemanticParams
from codeagent_lab.tools.semantic_openai import (
    SemanticIndexManager,
    SemanticOpenAITool,
)


def _create_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when unsupported."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported: {exc}")


class RecordingEmbedder:
    """Deterministic embedder used for testing."""

    name = "recording"

    def __init__(self) -> None:
        """Initialise the recording embedder state."""
        self.dimension = 3
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic embeddings and record calls."""
        self.calls.append(list(texts))
        return [self._encode(text) for text in texts]

    def _encode(self, text: str) -> list[float]:
        """Encode ``text`` into a simple keyword-based vector."""
        lowered = text.lower()
        return [
            1.0 if "sort" in lowered else 0.0,
            1.0 if "config" in lowered else 0.0,
            1.0 if "database" in lowered else 0.0,
        ]


class InMemoryIndex:
    """Simple cosine-similarity index persisted to disk for tests."""

    def __init__(self, dim: int) -> None:
        """Initialise the in-memory index state."""
        self.dim = dim
        self.name = "in-memory"
        self._matrix = np.zeros((0, dim), dtype="float32")
        self._ids: list[str] = []

    def build(self, vectors: np.ndarray, ids: list[str]) -> None:
        """Build the index from ``vectors`` and ``ids``."""
        matrix = self._prepare_matrix(vectors)
        self._ids = list(ids)
        if matrix.size == 0:
            self._matrix = np.zeros((0, self.dim), dtype="float32")
            return
        self._matrix = self._normalize(matrix)

    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        """Append vectors to the existing index."""
        matrix = self._prepare_matrix(vectors)
        if matrix.size == 0:
            return
        if not self._ids:
            self.build(matrix, ids)
            return
        self._ids.extend(ids)
        combined = np.vstack([self._matrix, self._normalize(matrix)])
        self._matrix = combined

    def search(self, queries: np.ndarray, topk: int) -> list[list[tuple[str, float]]]:
        """Search for the nearest documents to ``queries``."""
        query_matrix = self._prepare_matrix(queries)
        query_matrix = self._normalize(query_matrix)
        results: list[list[tuple[str, float]]] = []
        for row in query_matrix:
            if not self._ids:
                results.append([])
                continue
            scores = np.dot(self._matrix, row)
            ranked = sorted(
                ((self._ids[idx], float(score)) for idx, score in enumerate(scores)),
                key=lambda item: item[1],
                reverse=True,
            )
            results.append(ranked[:topk])
        return results

    def save(self, path: str | Path) -> None:
        """Persist the index to ``path``."""
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        np.save(target / "vectors.npy", self._matrix)
        with (target / "ids.json").open("w", encoding="utf-8") as handle:
            json.dump(self._ids, handle)

    def load(self, path: str | Path) -> None:
        """Load the index state from ``path``."""
        source = Path(path)
        self._matrix = np.asarray(np.load(source / "vectors.npy"), dtype="float32")
        with (source / "ids.json").open(encoding="utf-8") as handle:
            self._ids = list(json.load(handle))
        if self._matrix.ndim != 2 or self._matrix.shape[1] != self.dim:
            message = f"expected matrix with dim {self.dim}, received shape {self._matrix.shape}"
            raise ValueError(message)

    def _prepare_matrix(self, matrix: np.ndarray) -> np.ndarray:
        array = np.asarray(matrix, dtype="float32")
        if array.ndim != 2:
            message = f"expected 2d matrix, received shape {array.shape}"
            raise ValueError(message)
        if array.shape[1] != self.dim:
            message = f"vector dimension mismatch: expected {self.dim}, received {array.shape[1]}"
            raise ValueError(message)
        return array

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return matrix / norms


def test_index_manager_builds_and_reuses_index(tmp_path: Path) -> None:
    """The index manager builds once and reloads persisted state on reuse."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "a.py").write_text("Sort arrays.\n")
    (repo_root / "b.py").write_text("Configure systems.\n")

    index_root = tmp_path / "indexes"
    embedder = RecordingEmbedder()
    index = InMemoryIndex(embedder.dimension)
    manager = SemanticIndexManager(embedder, index, index_root)

    first_docs, first_built = manager.ensure_index(repo_root)

    assert first_built is True
    assert sorted(first_docs) == ["a.py", "b.py"]
    assert embedder.calls[0][0] == "Sort arrays.\n"

    reuse_embedder = RecordingEmbedder()
    reuse_index = InMemoryIndex(reuse_embedder.dimension)
    reuse_manager = SemanticIndexManager(reuse_embedder, reuse_index, index_root)

    second_docs, second_built = reuse_manager.ensure_index(repo_root)

    assert second_built is False
    assert second_docs == first_docs
    assert reuse_embedder.calls == []


def test_semantic_tool_builds_index_and_returns_hits(tmp_path: Path) -> None:
    """The semantic tool embeds files, persists an index, and ranks relevant hits."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "sorting.py").write_text("Implements sorting utilities for arrays.\n")
    (repo_root / "config.py").write_text("Configuration loader for services.\n")
    (repo_root / "database.py").write_text("Database connection helpers.\n")

    index_root = tmp_path / "indexes"
    embedder = RecordingEmbedder()
    index = InMemoryIndex(embedder.dimension)
    manager = SemanticIndexManager(embedder, index, index_root)
    tool = SemanticOpenAITool(embedder, manager)

    params = SemanticParams(query="How do we sort numbers?", root=str(repo_root), topk=5)
    result = tool.run(params)

    assert result.ok is True
    assert result.hits
    assert result.hits[0].path == "sorting.py"
    assert result.hits[0].score > 0
    assert embedder.calls[0]  # document embeddings recorded

    manifest = next(index_root.rglob("manifest.json"), None)
    assert manifest is not None


def test_semantic_tool_reuses_existing_index(tmp_path: Path) -> None:
    """When an index exists, only the query is embedded and the index is reused."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "sorting.py").write_text("Sorting helpers.\n")

    index_root = tmp_path / "indexes"
    initial_embedder = RecordingEmbedder()
    initial_index = InMemoryIndex(initial_embedder.dimension)
    initial_manager = SemanticIndexManager(initial_embedder, initial_index, index_root)
    tool = SemanticOpenAITool(initial_embedder, initial_manager)
    params = SemanticParams(query="Need to sort items", root=str(repo_root), topk=3)

    first_result = tool.run(params)
    assert first_result.hits[0].path == "sorting.py"

    reuse_embedder = RecordingEmbedder()
    reuse_index = InMemoryIndex(reuse_embedder.dimension)
    reuse_manager = SemanticIndexManager(reuse_embedder, reuse_index, index_root)
    reuse_tool = SemanticOpenAITool(reuse_embedder, reuse_manager)

    second_result = reuse_tool.run(params)

    assert second_result.hits[0].path == "sorting.py"
    assert len(reuse_embedder.calls) == 1
    assert reuse_embedder.calls[0] == [params.query]


def test_semantic_tool_rebuilds_when_load_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Indexes are rebuilt when loading persisted state fails."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "sorting.py").write_text("Sorting helpers.\n")

    index_root = tmp_path / "indexes"
    initial_embedder = RecordingEmbedder()
    initial_index = InMemoryIndex(initial_embedder.dimension)
    initial_manager = SemanticIndexManager(initial_embedder, initial_index, index_root)
    tool = SemanticOpenAITool(initial_embedder, initial_manager)
    params = SemanticParams(query="Need to sort items", root=str(repo_root), topk=3)

    # Persist an initial index.
    tool.run(params)

    def failing_load(_self: InMemoryIndex, _path: str | Path) -> None:
        raise RuntimeError("load failed")

    monkeypatch.setattr(InMemoryIndex, "load", failing_load, raising=True)

    rebuild_embedder = RecordingEmbedder()
    rebuild_index = InMemoryIndex(rebuild_embedder.dimension)
    rebuild_manager = SemanticIndexManager(rebuild_embedder, rebuild_index, index_root)
    rebuild_tool = SemanticOpenAITool(rebuild_embedder, rebuild_manager)

    result = rebuild_tool.run(params)

    assert result.ok is True
    assert result.meta["index"]["built"] is True
    assert rebuild_embedder.calls[0][0] == "Sorting helpers.\n"
    assert rebuild_embedder.calls[1] == [params.query]


def test_semantic_tool_reports_missing_root(tmp_path: Path) -> None:
    """Missing repositories are reported with ``ok=False``."""
    index_root = tmp_path / "indexes"
    embedder = RecordingEmbedder()
    index = InMemoryIndex(embedder.dimension)
    manager = SemanticIndexManager(embedder, index, index_root)
    tool = SemanticOpenAITool(embedder, manager)

    missing_root = tmp_path / "missing"
    params = SemanticParams(query="anything", root=str(missing_root))

    result = tool.run(params)

    assert result.ok is False
    assert result.hits == []
    assert result.meta["error"] == "root-missing"


def test_semantic_tool_ignores_symlinks_outside_root(tmp_path: Path) -> None:
    """Symlinked files outside the root are not indexed or searched."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "keep.txt").write_text("Sort the array.\n")

    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "secret.txt"
    external_file.write_text("Sort secrets outside.\n")

    _create_symlink(repo_root / "link.txt", external_file)

    index_root = tmp_path / "indexes"
    embedder = RecordingEmbedder()
    index = InMemoryIndex(embedder.dimension)
    manager = SemanticIndexManager(embedder, index, index_root)
    tool = SemanticOpenAITool(embedder, manager)

    params = SemanticParams(query="sort", root=str(repo_root), topk=5)
    result = tool.run(params)

    assert result.ok is True
    assert embedder.calls
    assert all("secret" not in text for text in embedder.calls[0])
    assert all(hit.path != "link.txt" for hit in result.hits)
