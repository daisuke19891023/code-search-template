"""Unit tests for the dependency injection container."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codeagent_lab.container import Container, build_container
from codeagent_lab.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Sequence
    import pytest


class _DummyEmbedding:
    """Minimal embedding backend used for container tests."""

    name = "dummy"

    def __init__(self, api_key: str | None, base_url: str | None, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.dimension = 7

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]


class _DummyVectorIndex:
    """Minimal vector index satisfying the protocol for tests."""

    def __init__(self, dim: int) -> None:
        self.name = "dummy-index"
        self.dim = dim

    def build(self, vectors: Any, ids: Sequence[str]) -> None:  # pragma: no cover - unused in tests
        self.last_build = (vectors, list(ids))

    def add(self, vectors: Any, ids: Sequence[str]) -> None:  # pragma: no cover - unused in tests
        self.last_add = (vectors, list(ids))

    def search(self, _queries: Any, _topk: int) -> list[list[tuple[str, float]]]:
        return [[]]

    def save(self, path: str) -> None:  # pragma: no cover - unused in tests
        self.saved_path = path

    def load(self, path: str) -> None:  # pragma: no cover - unused in tests
        self.loaded_path = path


def _base_settings(tmp_path: Any, **overrides: Any) -> Settings:
    """Create settings pointing storage paths to a temporary directory."""
    defaults: dict[str, Any] = {
        "duckdb_path": tmp_path / "experiments.duckdb",
        "parquet_root": tmp_path / "parquet",
        "index_root": tmp_path / "indexes",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_build_container_skips_semantic_when_backend_disabled(tmp_path: Any) -> None:
    """Semantic tooling is omitted when the backend is disabled via settings."""
    settings = _base_settings(tmp_path, semantic_embed_backend="none")
    container = build_container(settings=settings)

    assert isinstance(container, Container)
    assert container.embeddings is None
    assert container.vectordb is None
    assert "semantic" not in container.tools.registry


def test_build_container_registers_semantic_with_custom_vector_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any,
) -> None:
    """Embedding and vector backends respect the configured factory keys."""
    captured: dict[str, Any] = {}

    monkeypatch.setattr("codeagent_lab.container.OpenAIEmbedding", _DummyEmbedding)

    def fake_create_vector_index(backend: str, dim: int) -> _DummyVectorIndex:
        captured["backend"] = backend
        captured["dim"] = dim
        return _DummyVectorIndex(dim)

    monkeypatch.setattr(
        "codeagent_lab.container.create_vector_index",
        fake_create_vector_index,
    )

    settings = _base_settings(
        tmp_path,
        openai_api_key="test",
        vector_store_backend="custom-backend",
    )

    container = build_container(settings=settings)

    assert isinstance(container.embeddings, _DummyEmbedding)
    assert isinstance(container.vectordb, _DummyVectorIndex)
    assert "semantic" in container.tools.registry
    assert captured == {
        "backend": "custom-backend",
        "dim": container.embeddings.dimension,
    }
