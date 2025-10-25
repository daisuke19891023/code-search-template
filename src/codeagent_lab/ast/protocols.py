"""Protocols for AST language providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from tree_sitter import Language


class AstLanguageProvider(Protocol):
    """Protocol describing a provider for tree-sitter languages."""

    def get_languages(self, names: list[str]) -> dict[str, Language]:
        """Return a mapping of language names to tree-sitter Language objects."""
