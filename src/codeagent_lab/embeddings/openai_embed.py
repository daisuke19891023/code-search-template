"""OpenAI embedding backend placeholder."""

from __future__ import annotations


from openai import OpenAI

from codeagent_lab.embeddings.protocols import EmbeddingBackend


class OpenAIEmbedding(EmbeddingBackend):
    """Wrapper around the OpenAI embeddings API."""

    def __init__(self, api_key: str | None, base_url: str | None, model: str) -> None:
        """Initialise the embedding backend."""
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.name = f"openai:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for the supplied texts."""
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
