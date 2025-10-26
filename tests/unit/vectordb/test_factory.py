"""Tests for the vector index factory."""

from __future__ import annotations

import builtins
import sys
from typing import Any

import pytest

from codeagent_lab.vectordb.faiss_store import FaissIndex
from codeagent_lab.vectordb.factory import create_vector_index


def test_create_vector_index_returns_faiss() -> None:
    """The factory instantiates the FAISS backend when requested."""
    index = create_vector_index("faiss", dim=3)
    assert isinstance(index, FaissIndex)
    assert index.dim == 3


def test_create_vector_index_rejects_unknown_backend() -> None:
    """Unknown backends raise a ValueError."""
    with pytest.raises(ValueError, match="unknown vector backend"):
        create_vector_index("bogus", dim=1)


def test_create_vector_index_requires_faiss_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing FAISS dependencies surface a friendly ValueError."""
    monkeypatch.delitem(sys.modules, "codeagent_lab.vectordb.faiss_store", raising=False)

    original_import = builtins.__import__

    def failing_import(
        name: str,
        globals_: dict[str, Any] | None = None,
        locals_: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "codeagent_lab.vectordb.faiss_store":
            raise ImportError("mocked missing dependency")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", failing_import)

    with pytest.raises(ValueError, match="FAISS backend requires optional dependencies"):
        create_vector_index("faiss", dim=3)
