"""Tests for the vector index factory."""

from __future__ import annotations

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
