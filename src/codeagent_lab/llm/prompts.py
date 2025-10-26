"""Prompt loading utilities."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import jinja2

PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=1)
def _prompt_environment(root: Path) -> jinja2.Environment:
    """Return a cached Jinja environment for the prompt templates."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(root),
        autoescape=jinja2.select_autoescape(default=True, enabled_extensions=("yaml",)),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(name: str, context: dict[str, object] | None = None) -> str:
    """Render a named prompt template."""
    template = _prompt_environment(PROMPTS_ROOT).get_template(f"{name}.yaml")
    return template.render(context or {})


def reset_prompt_environment_cache() -> None:
    """Clear the cached prompt environment (useful for tests)."""
    _prompt_environment.cache_clear()
