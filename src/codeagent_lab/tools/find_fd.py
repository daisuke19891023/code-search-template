"""fd-based file discovery implementation."""

from __future__ import annotations

import re
import time
from pathlib import Path

from codeagent_lab.models import FindItem, FindParams, FindResult
from codeagent_lab.tools.protocols import Tool

SUPPORTED_TYPES = {"file", "directory"}


class FdTool(Tool[FindParams, FindResult]):
    """Execute file discovery similar to ``fd``."""

    name = "find.fd"
    Param = FindParams
    Result = FindResult

    def run(self, params: FindParams) -> FindResult:
        """Execute fd-style search using a Python fallback."""
        start = time.perf_counter()
        root = Path(params.root)

        if not root.is_dir():
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {"error": "root-missing", "root": str(root)}
            return FindResult(ok=False, items=[], latency_ms=latency_ms, meta=meta)

        type_filter = params.type_filter
        if type_filter is not None and type_filter not in SUPPORTED_TYPES:
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {"error": "invalid-type", "type": type_filter}
            return FindResult(ok=False, items=[], latency_ms=latency_ms, meta=meta)

        try:
            pattern = re.compile(params.pattern) if params.pattern else None
        except re.error as exc:  # pragma: no cover - defensive branch
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {
                "error": "invalid-pattern",
                "pattern": params.pattern,
                "message": str(exc),
            }
            return FindResult(ok=False, items=[], latency_ms=latency_ms, meta=meta)

        matched: list[FindItem] = []
        for candidate in root.rglob("*"):
            if type_filter == "file" and not candidate.is_file():
                continue
            if type_filter == "directory" and not candidate.is_dir():
                continue

            relative = candidate.relative_to(root)
            relative_str = str(relative)

            if pattern and not pattern.search(relative_str):
                continue

            matched.append(FindItem(path=relative_str))

        matched.sort(key=lambda item: item.path)

        latency_ms = int((time.perf_counter() - start) * 1000)
        meta = {
            "executor": "python-fallback",
            "pattern": params.pattern,
            "type": type_filter or "any",
            "count": len(matched),
        }
        return FindResult(ok=True, items=matched, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "List files using fd."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()
