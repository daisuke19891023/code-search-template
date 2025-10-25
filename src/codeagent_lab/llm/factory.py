"""Factory for LLM clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from codeagent_lab.settings import Settings


def create_openai_client(settings: Settings) -> OpenAI:
    """Create an OpenAI client using application settings."""
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
