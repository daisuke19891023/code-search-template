"""Protocols for embedding backends."""

from __future__ import annotations

from typing import Protocol


class EmbeddingBackend(Protocol):
    """Protocol describing an embedding backend."""

    name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed the given texts into dense vectors."""
