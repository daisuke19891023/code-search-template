"""Factory for LLM clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from codeagent_lab.settings import Settings


def create_openai_client(settings: Settings) -> OpenAI:
    """Create an OpenAI client using application settings."""
    api_key = settings.openai_api_key

    if not api_key:
        message = "OpenAI API key is not configured."
        raise ValueError(message)

    base_url = settings.openai_base_url
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)

    return OpenAI(api_key=api_key)
