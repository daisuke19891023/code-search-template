"""Tests for the OpenAI embedding backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from codeagent_lab.embeddings.openai_embed import OpenAIEmbedding


def _mock_response(embedding_length: int) -> MagicMock:
    item = MagicMock()
    item.embedding = [0.1] * embedding_length
    response = MagicMock()
    response.data = [item]
    return response


def test_openai_embedding_returns_expected_dimension() -> None:
    """The backend returns embeddings with the model-defined dimension."""
    with patch("codeagent_lab.embeddings.openai_embed.OpenAI") as openai_cls:
        client = openai_cls.return_value
        client.embeddings.create.return_value = _mock_response(embedding_length=3072)

        backend = OpenAIEmbedding(api_key="key", base_url="https://example.com", model="text-embedding-3-large")

        vectors = backend.embed(["hello"])

        assert backend.dimension == 3072
        assert len(vectors) == 1
        assert len(vectors[0]) == 3072
        assert all(isinstance(value, float) for value in vectors[0])


def test_openai_embedding_raises_on_dimension_mismatch() -> None:
    """A mismatch between expected and received dimensions raises an error."""
    with patch("codeagent_lab.embeddings.openai_embed.OpenAI") as openai_cls:
        client = openai_cls.return_value
        client.embeddings.create.return_value = _mock_response(embedding_length=10)

        backend = OpenAIEmbedding(api_key="key", base_url=None, model="text-embedding-3-small")

        with pytest.raises(ValueError, match="embedding dimension mismatch"):
            backend.embed(["hello"])


def test_openai_embedding_rejects_unknown_model() -> None:
    """Unsupported models are rejected to avoid silent dimension mismatches."""
    with pytest.raises(ValueError, match="unsupported embedding model"):
        OpenAIEmbedding(api_key="key", base_url=None, model="unknown-model")
