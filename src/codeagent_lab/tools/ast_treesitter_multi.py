"""Tree-sitter based AST tool implementation."""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from fnmatch import fnmatch
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from codeagent_lab.models import AstFinding, AstParams, AstResult
from codeagent_lab.tools.protocols import Tool

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeagent_lab.ast.protocols import AstLanguageProvider, QueryBundle
    from tree_sitter import Language


DEFAULT_FILE_GLOBS: dict[str, tuple[str, ...]] = {"python": ("*.py",)}
VALID_QUERY_KINDS: set[str] = {"def", "ref", "call", "note"}


def _load_default_queries(language: str) -> dict[str, str]:
    """Load query sections from ``ast/queries/<language>.scm`` if available."""
    package = "codeagent_lab.ast.queries"
    try:
        data = (resources.files(package) / f"{language}.scm").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return {}

    sections: dict[str, list[str]] = {}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current
        if current and buffer:
            sections[current] = buffer.copy()
        buffer.clear()

    for raw_line in data.splitlines():
        line = raw_line.strip()
        if line.startswith("; query:"):
            flush()
            current = line.split(":", 1)[1].strip()
            continue
        if not current:
            continue
        buffer.append(raw_line)

    flush()
    return {key: "\n".join(lines).strip() for key, lines in sections.items() if lines}


def _relative_path(root: Path, path: Path) -> str:
    """Return the ``path`` relative to ``root`` with POSIX separators."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    return relative.as_posix()


@dataclass
class _QueryContext:
    parser: Any
    queries: dict[str, Any]


class TreeSitterTool(Tool[AstParams, AstResult]):
    """Inspect syntax trees using tree-sitter queries."""

    name = "ast.tree_sitter"
    Param = AstParams
    Result = AstResult

    def __init__(
        self,
        provider: AstLanguageProvider,
        queries: Mapping[str, QueryBundle] | None = None,
        file_globs: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        """Initialise the tree-sitter tool with providers and query overrides."""
        self._provider = provider
        overrides = queries or {}
        self._query_overrides: dict[str, dict[str, str]] = {
            language: dict(bundle)
            for language, bundle in overrides.items()
        }
        self._file_globs = dict(DEFAULT_FILE_GLOBS)
        if file_globs:
            for language, patterns in file_globs.items():
                self._file_globs[language] = tuple(patterns)
        self._query_text_cache: dict[str, dict[str, str]] = {}

    def run(self, params: AstParams) -> AstResult:
        """Execute AST analysis for the requested languages."""
        start = time.perf_counter()
        root = Path(params.root)
        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            return AstResult(
                ok=False,
                findings=[],
                latency_ms=latency_ms,
                meta={"error": "root-missing", "root": str(root)},
            )

        languages = self._provider.get_languages(params.languages)
        missing = sorted(name for name in params.languages if name not in languages)
        if not languages:
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {"error": "language-unavailable", "requested": list(params.languages)}
            if missing:
                meta["missing_languages"] = missing
            return AstResult(ok=False, findings=[], latency_ms=latency_ms, meta=meta)

        findings = self._scan_languages(root, languages, params)
        findings.sort(key=lambda finding: (finding.path, finding.line, finding.kind, finding.text))

        latency_ms = int((time.perf_counter() - start) * 1000)
        meta: dict[str, object] = {
            "executor": "tree-sitter",
            "languages": sorted(languages.keys()),
            "match_count": len(findings),
        }
        if missing:
            meta["missing_languages"] = missing

        return AstResult(ok=True, findings=findings, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Inspect syntax trees using tree-sitter."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    # Internal helpers -------------------------------------------------

    def _scan_languages(
        self,
        root: Path,
        languages: Mapping[str, Language],
        params: AstParams,
    ) -> list[AstFinding]:
        """Scan the repository for AST findings."""
        contexts = {name: self._build_context(name, language) for name, language in languages.items()}
        findings: list[AstFinding] = []
        seen: set[tuple[str, str, int, str]] = set()
        scope_globs = tuple(params.scope_globs or [])

        for language_name, context in contexts.items():
            patterns = self._file_globs.get(language_name, ("*",))
            processed: set[str] = set()
            for pattern in patterns:
                for file_path in root.rglob(pattern):
                    if not file_path.is_file():
                        continue
                    relative = _relative_path(root, file_path)
                    if relative in processed:
                        continue
                    processed.add(relative)
                    if scope_globs and not any(fnmatch(relative, glob_pattern) for glob_pattern in scope_globs):
                        continue
                    findings.extend(
                        self._scan_file(
                            context=context,
                            file_path=file_path,
                            relative_path=relative,
                            symbol_filter=params.symbol,
                            seen=seen,
                        ),
                    )
        return findings

    def _build_context(self, name: str, language: Language) -> _QueryContext:
        """Construct parser and query objects for a language."""
        tree_sitter = importlib.import_module("tree_sitter")
        parser = tree_sitter.Parser()
        parser.set_language(language)

        query_sources = self._queries_for_language(name)
        queries: dict[str, Any] = {}
        for kind, source in query_sources.items():
            if not source.strip():
                continue
            queries[kind] = tree_sitter.Query(language, source)
        return _QueryContext(parser=parser, queries=queries)

    def _queries_for_language(self, language: str) -> dict[str, str]:
        """Return query text for the provided language."""
        if language not in self._query_text_cache:
            defaults = _load_default_queries(language)
            overrides = self._query_overrides.get(language, {})
            merged: dict[str, str] = {**defaults, **overrides}
            self._query_text_cache[language] = merged
        return self._query_text_cache[language]

    def _scan_file(
        self,
        *,
        context: _QueryContext,
        file_path: Path,
        relative_path: str,
        symbol_filter: str | None,
        seen: set[tuple[str, str, int, str]],
    ) -> list[AstFinding]:
        """Scan a file with the configured queries."""
        try:
            source_bytes = file_path.read_bytes()
        except OSError:
            return []

        source_text = source_bytes.decode("utf-8", errors="ignore")
        lines = source_text.splitlines()

        tree = context.parser.parse(source_bytes)
        results: list[AstFinding] = []
        for query_kind, query_obj in context.queries.items():
            if query_kind not in VALID_QUERY_KINDS:
                continue
            captures = cast("list[tuple[Any, str]]", query_obj.captures(tree.root_node))
            kind_literal = cast("Literal['def', 'ref', 'call', 'note']", query_kind)
            for node, capture_name in captures:
                if not capture_name.endswith(".name"):
                    continue
                identifier_bytes = source_bytes[node.start_byte: node.end_byte]
                identifier = identifier_bytes.decode("utf-8", errors="ignore")
                if symbol_filter and identifier != symbol_filter:
                    continue
                start_point = cast("tuple[int, int]", node.start_point)
                line_no = start_point[0] + 1
                if line_no - 1 >= len(lines) or line_no <= 0:
                    continue
                record_key = (kind_literal, relative_path, line_no, identifier)
                if record_key in seen:
                    continue
                seen.add(record_key)
                results.append(
                    AstFinding(
                        kind=kind_literal,
                        path=relative_path,
                        line=line_no,
                        text=identifier,
                    ),
                )
        return results
