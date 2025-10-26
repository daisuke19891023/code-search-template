"""Tests for the prompt rendering utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import jinja2
import pytest

from codeagent_lab.llm import prompts

if TYPE_CHECKING:
    from pathlib import Path


def test_render_prompt_renders_with_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Render a template with provided context values."""
    (tmp_path / "greeting.yaml").write_text("Hello {{ name }}!", encoding="utf-8")

    monkeypatch.setattr(prompts, "PROMPTS_ROOT", tmp_path)
    prompts.reset_prompt_environment_cache()

    rendered = prompts.render_prompt("greeting", {"name": "world"})

    assert rendered == "Hello world!"


def test_render_prompt_raises_for_missing_variables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise when the template references an undefined variable."""
    (tmp_path / "needs.yaml").write_text("{{ required }}", encoding="utf-8")

    monkeypatch.setattr(prompts, "PROMPTS_ROOT", tmp_path)
    prompts.reset_prompt_environment_cache()

    with pytest.raises(jinja2.exceptions.UndefinedError):
        prompts.render_prompt("needs")
