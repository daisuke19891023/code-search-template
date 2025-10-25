"""Factory helpers for vector stores."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeagent_lab.vectordb.faiss_store import FaissIndex

if TYPE_CHECKING:
    from codeagent_lab.vectordb.protocols import VectorIndex


def create_vector_index(backend: str, dim: int) -> VectorIndex:
    """Create a vector index for the requested backend."""
    if backend == "faiss":
        return FaissIndex(dim)
    message = f"unknown vector backend: {backend}"
    raise ValueError(message)
