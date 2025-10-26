"""Ripgrep-inspired search tool with a pure-Python implementation."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from codeagent_lab.models import GrepHit, GrepParams, GrepResult
from codeagent_lab.tools._path_filters import resolve_within_root
from codeagent_lab.tools.protocols import Tool


class RipgrepTool(Tool[GrepParams, GrepResult]):
    """Execute ripgrep and map its JSON output into ``GrepResult`` objects."""

    name = "grep.ripgrep"
    Param = GrepParams
    Result = GrepResult

    def run(self, params: GrepParams) -> GrepResult:
        """Execute ripgrep search and convert matches into model instances."""
        root = Path(params.root)
        start = time.perf_counter()
        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            return GrepResult(
                ok=False,
                hits=[],
                latency_ms=latency_ms,
                meta={"error": "root-missing", "root": str(root)},
            )

        try:
            hits = self._python_search(root, params.pattern)
        except re.error as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta: dict[str, Any] = {
                "error": "invalid-pattern",
                "pattern": params.pattern,
                "message": str(exc),
                "exit_code": 2,
            }
            return GrepResult(ok=False, hits=[], latency_ms=latency_ms, meta=meta)

        latency_ms = int((time.perf_counter() - start) * 1000)
        exit_code = 0 if hits else 1
        meta: dict[str, Any] = {
            "executor": "python-fallback",
            "pattern": params.pattern,
            "exit_code": exit_code,
        }
        return GrepResult(ok=True, hits=hits, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search files using ripgrep."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    @staticmethod
    def _python_search(root: Path, pattern: str) -> list[GrepHit]:
        """Search files using a pure Python implementation."""
        regex = re.compile(pattern)
        hits: list[GrepHit] = []
        resolved_root = root.resolve()
        for file_path in root.rglob("*"):
            resolved = resolve_within_root(resolved_root, file_path)
            if resolved is None or not resolved.is_file():
                continue
            try:
                content = resolved.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                if not regex.search(line):
                    continue
                try:
                    relative = resolved.relative_to(resolved_root)
                except ValueError:
                    relative = resolved
                hits.append(
                    GrepHit(path=str(relative), line=line_number, text=line.rstrip("\n")),
                )
        return hits
