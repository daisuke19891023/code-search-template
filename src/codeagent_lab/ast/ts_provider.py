"""Tree-sitter language provider placeholder."""

from __future__ import annotations


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Language

from codeagent_lab.ast.protocols import AstLanguageProvider


class TreeSitterProvider(AstLanguageProvider):
    """Load tree-sitter languages from configured shared libraries."""

    def __init__(self, library_paths: dict[str, str]) -> None:
        """Initialise the provider with language library paths."""
        self._library_paths = library_paths

    def get_languages(self, names: list[str]) -> dict[str, Language]:
        """Return loaded languages for the requested identifiers."""
        languages: dict[str, Language] = {}
        for name in names:
            path = self._library_paths.get(name)
            if path is None:
                continue
            from tree_sitter import Language

            languages[name] = Language(path, name)
        return languages
