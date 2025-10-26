"""Factory helpers for vector stores."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeagent_lab.vectordb.faiss_store import FaissIndex
    from codeagent_lab.vectordb.protocols import VectorIndex


def create_vector_index(backend: str, dim: int) -> VectorIndex:
    """Create a vector index for the requested backend."""
    if backend == "faiss":
        try:
            from codeagent_lab.vectordb.faiss_store import FaissIndex
        except ImportError as exc:
            message = (
                "FAISS backend requires optional dependencies. Install the faiss package "
                "before creating a FAISS vector index."
            )
            raise ValueError(message) from exc
        index: FaissIndex = FaissIndex(dim)
        return index
    message = f"unknown vector backend: {backend}"
    raise ValueError(message)
