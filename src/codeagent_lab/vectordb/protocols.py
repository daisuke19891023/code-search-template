"""Protocols for vector index implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence
    import numpy as np


class VectorIndex(Protocol):
    """Protocol describing a vector index."""

    name: str
    dim: int

    def build(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        """Create an index from vectors and identifiers."""
        ...

    def add(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        """Add vectors to an existing index."""
        ...

    def search(self, queries: np.ndarray, topk: int) -> list[list[tuple[str, float]]]:
        """Search the index returning ids and scores."""
        ...

    def save(self, path: str) -> None:
        """Persist the index to the filesystem."""
        ...

    def load(self, path: str) -> None:
        """Load the index from the filesystem."""
        ...
