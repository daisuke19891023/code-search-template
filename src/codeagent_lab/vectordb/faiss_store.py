"""FAISS index wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import faiss
import numpy as np

from codeagent_lab.vectordb.protocols import VectorIndex

if TYPE_CHECKING:
    from collections.abc import Sequence


class FaissIndex(VectorIndex):
    """Inner-product FAISS index wrapper."""

    def __init__(self, dim: int) -> None:
        """Initialise the FAISS index wrapper."""
        self.dim = dim
        self.name = "faiss:ip"
        self._index = faiss.IndexFlatIP(dim)
        self._ids: list[str] = []

    def build(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        """Create a new index from the supplied vectors and identifiers."""
        self._ids = list(ids)
        self._index = faiss.IndexFlatIP(self.dim)
        self._index.add(self._normalize(vectors))

    def add(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        """Append vectors and identifiers to the existing index."""
        self._ids.extend(ids)
        self._index.add(self._normalize(vectors))

    def search(self, queries: np.ndarray, topk: int) -> list[list[tuple[str, float]]]:
        """Search the index and return ranked identifiers per query."""
        distances, indices = self._index.search(self._normalize(queries), topk)
        results: list[list[tuple[str, float]]] = []
        for row, dist_row in zip(indices, distances, strict=True):
            hits: list[tuple[str, float]] = []
            for idx, score in zip(row, dist_row, strict=True):
                if idx == -1:
                    continue
                hits.append((self._ids[idx], float(score)))
            results.append(hits)
        return results

    def save(self, path: str | Path) -> None:
        """Persist the index data to disk."""
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(target / "index.faiss"))
        with (target / "ids.json").open("w", encoding="utf-8") as handle:
            json.dump(self._ids, handle)

    def load(self, path: str | Path) -> None:
        """Load index data from disk."""
        source = Path(path)
        self._index = faiss.read_index(str(source / "index.faiss"))
        with (source / "ids.json").open(encoding="utf-8") as handle:
            self._ids = list(json.load(handle))

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
        return matrix / norms
