"""Ripgrep-inspired search tool with a pure-Python implementation."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, TYPE_CHECKING, Any, TextIO, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

from codeagent_lab.models import GrepHit, GrepParams, GrepResult
from codeagent_lab.tools._path_filters import resolve_within_root
from codeagent_lab.tools.protocols import Tool


class RipgrepExecutionError(RuntimeError):
    """Raised when ripgrep finishes with an unexpected status."""

    def __init__(self, reason: dict[str, Any]) -> None:
        """Initialise the exception with structured error details."""
        message = reason.get("message") or reason.get("error") or "ripgrep failed"
        super().__init__(message)
        self.reason = reason


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

        fallback_reason: dict[str, Any] | None = None
        try:
            ripgrep_hits, ripgrep_meta, exit_code = self._ripgrep_search(root, params)
        except FileNotFoundError:
            fallback_reason = {
                "error": "ripgrep-missing",
                "message": "rg executable not found in PATH",
            }
        except RipgrepExecutionError as exc:
            fallback_reason = exc.reason
        else:
            latency_ms = int((time.perf_counter() - start) * 1000)
            ripgrep_meta.update({
                "pattern": params.pattern,
                "exit_code": exit_code,
            })
            ok = exit_code in (0, 1)
            return GrepResult(ok=ok, hits=ripgrep_hits, latency_ms=latency_ms, meta=ripgrep_meta)

        try:
            hits = self._python_search(root, params.pattern)
        except re.error as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            meta = {
                "executor": "python-fallback",
                "error": "invalid-pattern",
                "pattern": params.pattern,
                "message": str(exc),
                "exit_code": 2,
                "fallback_reason": fallback_reason,
            }
            return GrepResult(ok=False, hits=[], latency_ms=latency_ms, meta=meta)

        latency_ms = int((time.perf_counter() - start) * 1000)
        exit_code = 0 if hits else 1
        meta = {
            "executor": "python-fallback",
            "pattern": params.pattern,
            "exit_code": exit_code,
            "fallback_reason": fallback_reason,
        }
        return GrepResult(ok=True, hits=hits, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search files using ripgrep."

    def json_schema(self) -> dict[str, object]:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    def _ripgrep_search(
        self, root: Path, params: GrepParams,
    ) -> tuple[list[GrepHit], dict[str, Any], int]:
        """Execute ripgrep and transform its JSON events into ``GrepHit`` objects."""
        process = self._spawn_ripgrep(root, params.pattern)
        stdout = cast("TextIO", self._ensure_pipe(process.stdout, "stdout"))
        stderr = self._ensure_pipe(process.stderr, "stderr")

        hits, summary_data, unparsed_events = self._collect_ripgrep_events(stdout, root)

        exit_code = process.wait()
        stderr_output = stderr.read().strip()
        stderr.close()

        if exit_code not in (0, 1):
            raise RipgrepExecutionError(
                self._build_failure_reason(exit_code, stderr_output, unparsed_events),
            )

        meta = self._build_success_meta(len(hits), summary_data, stderr_output, unparsed_events)
        return hits, meta, exit_code

    def _spawn_ripgrep(self, root: Path, pattern: str) -> Popen[str]:
        """Start a ripgrep process configured for JSON output."""
        process = Popen(
            ["/usr/bin/env", "rg", "--json", "--file", "-", "."],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            cwd=str(root),
            text=True,
        )
        self._send_pattern(process, pattern)
        return process

    @staticmethod
    def _ensure_pipe(pipe: IO[str] | None, name: str) -> IO[str]:
        """Ensure ``subprocess.PIPE`` descriptors are available."""
        if pipe is None:
            raise RipgrepExecutionError(
                {
                    "error": "ripgrep-pipe",
                    "message": f"failed to capture ripgrep {name}",
                },
            )
        return pipe

    def _send_pattern(self, process: Popen[str], pattern: str) -> None:
        """Send the search pattern to ripgrep via stdin."""
        stdin_pipe = self._ensure_pipe(process.stdin, "stdin")
        try:
            stdin_pipe.write(pattern)
            stdin_pipe.write("\n")
            stdin_pipe.flush()
        except OSError as exc:
            stdin_pipe.close()
            process.kill()
            process.wait()
            raise RipgrepExecutionError(
                {
                    "error": "ripgrep-stdin",
                    "message": f"failed to send pattern: {exc}",
                },
            ) from exc
        stdin_pipe.close()

    def _collect_ripgrep_events(
        self, stdout: TextIO, root: Path,
    ) -> tuple[list[GrepHit], dict[str, Any] | None, list[str]]:
        """Stream ripgrep JSON events into application models."""
        hits: list[GrepHit] = []
        summary_data: dict[str, Any] | None = None
        unparsed_events: list[str] = []
        resolved_root = root.resolve()

        for event_type, payload in self._ripgrep_events(stdout):
            if event_type == "match":
                hit = self._build_grep_hit(payload, resolved_root)
                if hit is not None:
                    hits.append(hit)
            elif event_type == "summary":
                summary_data = payload
            elif event_type is None:
                unparsed_events.append(cast("str", payload["raw"]))

        stdout.close()
        return hits, summary_data, unparsed_events

    def _ripgrep_events(self, stdout: TextIO) -> Iterator[tuple[str | None, dict[str, Any]]]:
        """Yield parsed ripgrep events or capture malformed lines."""
        for raw_line in stdout:
            stripped_line = raw_line.strip()
            if not stripped_line:
                continue
            try:
                event = json.loads(stripped_line)
            except json.JSONDecodeError:
                yield None, {"raw": stripped_line}
                continue
            event_type = cast("str | None", event.get("type"))
            payload = cast("dict[str, Any]", event.get("data", {}))
            yield event_type, payload

    def _build_grep_hit(self, data: dict[str, Any], resolved_root: Path) -> GrepHit | None:
        """Convert a ripgrep ``match`` event into a :class:`GrepHit`."""
        path_info = cast("dict[str, Any]", data.get("path", {}))
        path_text = cast("str | None", path_info.get("text"))
        if path_text is None:
            return None
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        resolved = resolve_within_root(resolved_root, candidate)
        if resolved is None:
            return None
        try:
            relative = resolved.relative_to(resolved_root)
        except ValueError:
            relative = resolved
        line_number = data.get("line_number")
        if line_number is None:
            return None
        try:
            line_number_int = int(line_number)
        except (TypeError, ValueError):
            return None
        lines_info = cast("dict[str, Any]", data.get("lines", {}))
        line_text = cast("str", lines_info.get("text", "")).rstrip("\n")
        return GrepHit(path=str(relative), line=line_number_int, text=line_text)

    @staticmethod
    def _build_failure_reason(
        exit_code: int, stderr_output: str, unparsed_events: list[str],
    ) -> dict[str, Any]:
        """Return structured metadata describing a ripgrep failure."""
        reason: dict[str, Any] = {"error": "ripgrep-exit", "exit_code": exit_code}
        if stderr_output:
            reason["stderr"] = stderr_output
        if unparsed_events:
            reason["unparsed_events"] = unparsed_events
        return reason

    @staticmethod
    def _build_success_meta(
        matches: int,
        summary_data: dict[str, Any] | None,
        stderr_output: str,
        unparsed_events: list[str],
    ) -> dict[str, Any]:
        """Create metadata describing a successful ripgrep invocation."""
        meta: dict[str, Any] = {"executor": "ripgrep", "matches": matches}
        if summary_data is not None:
            meta["summary"] = summary_data
        if stderr_output:
            meta["stderr"] = stderr_output
        if unparsed_events:
            meta["unparsed_events"] = unparsed_events
        return meta

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
