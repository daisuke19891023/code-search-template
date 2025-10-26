"""fd-based file discovery implementation."""

from __future__ import annotations

import re
import time
from pathlib import Path

from codeagent_lab.models import FindItem, FindParams, FindResult
from codeagent_lab.tools._path_filters import resolve_within_root
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
        resolved_root = root.resolve()
        for candidate in root.rglob("*"):
            resolved = resolve_within_root(resolved_root, candidate)
            if resolved is None:
                continue
            if type_filter == "file" and not resolved.is_file():
                continue
            if type_filter == "directory" and not resolved.is_dir():
                continue

            try:
                relative = resolved.relative_to(resolved_root)
            except ValueError:
                continue
            relative_str = relative.as_posix()

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
