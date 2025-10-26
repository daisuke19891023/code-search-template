"""OpenAI embedding backend implementation."""

from __future__ import annotations


from typing import TYPE_CHECKING

from openai import OpenAI

from codeagent_lab.embeddings.protocols import EmbeddingBackend

if TYPE_CHECKING:
    from collections.abc import Sequence


MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}


class OpenAIEmbedding(EmbeddingBackend):
    """Wrapper around the OpenAI embeddings API."""

    def __init__(self, api_key: str | None, base_url: str | None, model: str) -> None:
        """Initialise the embedding backend."""
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        try:
            self.dimension = MODEL_DIMENSIONS[model]
        except KeyError as error:
            message = f"unsupported embedding model: {model}"
            raise ValueError(message) from error
        self.model = model
        self.name = f"openai:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for the supplied texts."""
        response = self.client.embeddings.create(model=self.model, input=texts)
        vectors: list[list[float]] = []
        for item in response.data:
            vector = _to_float_list(item.embedding)
            if len(vector) != self.dimension:
                message = (
                    "embedding dimension mismatch: "
                    f"expected {self.dimension}, received {len(vector)}"
                )
                raise ValueError(message)
            vectors.append(vector)
        return vectors


def _to_float_list(values: Sequence[float]) -> list[float]:
    """Convert a sequence of floats to a list of built-in floats."""
    return [float(value) for value in values]
