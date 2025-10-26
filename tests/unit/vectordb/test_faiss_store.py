"""Tests for the FaissIndex wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from codeagent_lab.vectordb.faiss_store import FaissIndex


if TYPE_CHECKING:
    from pathlib import Path


def test_faiss_build_save_load_search(tmp_path: Path) -> None:
    """Building, saving, loading, and searching preserves results."""
    dim = 4
    index = FaissIndex(dim)
    vectors = np.array(
        [
            [0.9, 0.1, 0.0, 0.0],
            [0.0, 0.8, 0.2, 0.0],
            [0.1, 0.1, 0.7, 0.1],
        ],
        dtype="float32",
    )
    ids = ["a", "b", "c"]
    index.build(vectors, ids)

    query = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")

    original_results = index.search(query, topk=2)
    index.save(tmp_path)

    restored = FaissIndex(dim)
    restored.load(tmp_path)
    restored_results = restored.search(query, topk=2)

    assert [hit[0] for hit in original_results[0]] == [hit[0] for hit in restored_results[0]]
    for (_, score_a), (_, score_b) in zip(original_results[0], restored_results[0], strict=True):
        assert pytest.approx(score_a, rel=1e-6, abs=1e-6) == score_b


def test_faiss_add_appends_vectors() -> None:
    """Adding vectors grows the index and maintains order in search results."""
    index = FaissIndex(2)
    base_vectors = np.array([[1.0, 0.0]], dtype="float32")
    index.build(base_vectors, ["base"])

    new_vectors = np.array([[0.0, 1.0]], dtype="float32")
    index.add(new_vectors, ["new"])

    query = np.array([[0.0, 1.0]], dtype="float32")
    results = index.search(query, topk=2)[0]

    assert results[0][0] == "new"
    assert results[1][0] == "base"


def test_faiss_search_rejects_invalid_topk() -> None:
    """A non-positive top-k value raises an error."""
    index = FaissIndex(2)
    vectors = np.array([[1.0, 0.0]], dtype="float32")
    index.build(vectors, ["a"])

    with pytest.raises(ValueError, match="topk must be positive"):
        index.search(np.array([[1.0, 0.0]], dtype="float32"), topk=0)
