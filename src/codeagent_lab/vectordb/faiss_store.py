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
        matrix = self._prepare_matrix(vectors)
        id_list = list(ids)
        self._validate_id_count(matrix, id_list)
        self._ids = id_list
        self._index = faiss.IndexFlatIP(self.dim)
        self._index.add(self._normalize(matrix))

    def add(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        """Append vectors and identifiers to the existing index."""
        matrix = self._prepare_matrix(vectors)
        id_list = list(ids)
        self._validate_id_count(matrix, id_list)
        self._ids.extend(id_list)
        self._index.add(self._normalize(matrix))

    def search(self, queries: np.ndarray, topk: int) -> list[list[tuple[str, float]]]:
        """Search the index and return ranked identifiers per query."""
        if topk <= 0:
            message = f"topk must be positive, received {topk}"
            raise ValueError(message)
        matrix = self._prepare_matrix(queries)
        distances, indices = self._index.search(self._normalize(matrix), topk)
        results: list[list[tuple[str, float]]] = []
        for row, dist_row in zip(indices, distances, strict=True):
            hits: list[tuple[str, float]] = []
            index_values = [int(value) for value in row]
            score_values = [float(value) for value in dist_row]
            for idx, score in zip(index_values, score_values, strict=True):
                if idx == -1:
                    continue
                hits.append((self._ids[idx], score))
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
        self.dim = self._index.d
        with (source / "ids.json").open(encoding="utf-8") as handle:
            self._ids = list(json.load(handle))
        if len(self._ids) != self._index.ntotal:
            message = "identifier count does not match index entries"
            raise ValueError(message)

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
        return matrix / norms

    def _prepare_matrix(self, matrix: np.ndarray) -> np.ndarray:
        array = np.asarray(matrix, dtype="float32")
        expected_ndim = 2
        if array.ndim != expected_ndim:
            message = f"expected 2d matrix, received shape {array.shape}"
            raise ValueError(message)
        if array.shape[1] != self.dim:
            message = f"vector dimension mismatch: expected {self.dim}, received {array.shape[1]}"
            raise ValueError(message)
        return array

    def _validate_id_count(self, matrix: np.ndarray, ids: list[str]) -> None:
        if matrix.shape[0] != len(ids):
            message = (
                "identifier count mismatch: "
                f"received {len(ids)} ids for {matrix.shape[0]} vectors"
            )
            raise ValueError(message)
