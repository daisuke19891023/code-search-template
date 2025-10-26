"""Tests for the OpenAI client factory."""

from __future__ import annotations

import pytest

from codeagent_lab.llm import factory
from codeagent_lab.settings import Settings


def test_create_openai_client_requires_api_key() -> None:
    """Raise a helpful error when the API key is missing."""
    settings = Settings()

    with pytest.raises(ValueError, match="API key is not configured"):
        factory.create_openai_client(settings)


def test_create_openai_client_passes_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Instantiate the OpenAI client with provided configuration."""
    captured_kwargs: dict[str, object] = {}

    class DummyClient:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(factory, "OpenAI", DummyClient)

    settings = Settings(openai_api_key="secret", openai_base_url="https://example.com")

    client = factory.create_openai_client(settings)

    assert isinstance(client, DummyClient)
    assert captured_kwargs == {"api_key": "secret", "base_url": "https://example.com"}


def test_create_openai_client_omits_empty_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exclude optional parameters when they are unset."""
    captured_kwargs: dict[str, object] = {}

    class DummyClient:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(factory, "OpenAI", DummyClient)

    settings = Settings(openai_api_key="secret", openai_base_url=None)

    factory.create_openai_client(settings)

    assert captured_kwargs == {"api_key": "secret"}
