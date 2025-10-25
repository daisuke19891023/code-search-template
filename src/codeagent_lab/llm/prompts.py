"""Prompt loading utilities."""

from __future__ import annotations

from pathlib import Path

import jinja2

PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"


def render_prompt(name: str, context: dict[str, object] | None = None) -> str:
    """Render a named prompt template."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(PROMPTS_ROOT),
        autoescape=jinja2.select_autoescape(default=True, enabled_extensions=("yaml",)),
    )
    template = env.get_template(f"{name}.yaml")
    return template.render(context or {})
