"""Tree-sitter language provider implementation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from codeagent_lab.ast.protocols import AstLanguageProvider

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from tree_sitter import Language


class TreeSitterProvider(AstLanguageProvider):
    """Load tree-sitter languages from Python modules or shared libraries."""

    def __init__(self, sources: Mapping[str, str | Path] | None = None) -> None:
        """Initialise the provider with optional language sources."""
        self._sources: dict[str, str | Path] = {}
        if sources:
            for language, source in sources.items():
                self._sources[language] = self._normalise_source(source)
        self._cache: dict[str, Language] = {}

    def get_languages(self, names: Sequence[str]) -> dict[str, Language]:
        """Return loaded languages for the requested identifiers."""
        languages: dict[str, Language] = {}
        for name in names:
            if name in self._cache:
                languages[name] = self._cache[name]
                continue

            source = self._sources.get(name)
            language = self._load_from_source(name, source) if source is not None else self._load_from_default(name)
            if language is None:
                continue

            self._cache[name] = language
            languages[name] = language
        return languages

    def _load_from_source(self, name: str, source: str | Path) -> Language | None:
        """Load a language from an explicit source mapping."""
        if isinstance(source, Path):
            from tree_sitter import Language as TreeLanguage

            return TreeLanguage(str(source), name)

        path_candidate = Path(source)
        if path_candidate.exists():
            from tree_sitter import Language as TreeLanguage

            return TreeLanguage(str(path_candidate), name)
        return self._load_from_module(str(source))

    def _load_from_default(self, name: str) -> Language | None:
        """Attempt to import a language module using the canonical naming scheme."""
        module_name = f"tree_sitter_{name.replace('-', '_')}"
        return self._load_from_module(module_name)

    def _load_from_module(self, module_name: str) -> Language | None:
        """Load a language by importing a module with a ``language`` factory."""
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            return None

        language = self._resolve_language(getattr(module, "language", None))
        if language is not None:
            return language

        language = self._resolve_language(getattr(module, "LANGUAGE", None))
        if language is not None:
            return language

        return None

    @staticmethod
    def _resolve_language(candidate: object) -> Language | None:
        """Return a ``Language`` instance if ``candidate`` is callable."""
        if not callable(candidate):
            return None

        result = candidate()
        from tree_sitter import Language as TreeLanguage

        if isinstance(result, TreeLanguage):
            return result

        return None

    @staticmethod
    def _normalise_source(source: str | Path) -> str | Path:
        """Return a module path or filesystem path for the provided source."""
        if isinstance(source, Path):
            return source

        candidate = Path(source)
        if candidate.exists():
            return candidate

        return source
