"""Protocols for AST language providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from tree_sitter import Language


QueryBundle: TypeAlias = "Mapping[str, str]"
"""Mapping of query identifiers (``def``/``ref``/``call``/``note``) to source text."""


class AstLanguageProvider(Protocol):
    """Protocol describing a provider for tree-sitter languages."""

    def get_languages(self, names: Sequence[str]) -> Mapping[str, Language]:
        """Return a mapping of language names to tree-sitter ``Language`` objects."""
        ...
