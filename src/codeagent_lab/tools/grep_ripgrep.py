"""Ripgrep-based search tool using the ``rg`` executable."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from codeagent_lab.models import GrepHit, GrepParams, GrepResult
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
            completed = subprocess.run(
                [
                    "/usr/bin/env",
                    "rg",
                    "--json",
                    "-n",
                    "-S",
                    "--hidden",
                    "-f",
                    "-",
                    ".",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=params.timeout_s,
                cwd=str(root),
                input=f"{params.pattern}\n",
            )
        except FileNotFoundError:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return GrepResult(
                ok=False,
                hits=[],
                latency_ms=latency_ms,
                meta={
                    "error": "rg-not-found",
                    "command": [
                        "/usr/bin/env",
                        "rg",
                        "--json",
                        "-n",
                        "-S",
                        "--hidden",
                        "-f",
                        "-",
                        ".",
                    ],
                },
            )
        except subprocess.TimeoutExpired as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return GrepResult(
                ok=False,
                hits=[],
                latency_ms=latency_ms,
                meta={
                    "error": "timeout",
                    "timeout_s": params.timeout_s,
                    "command": [
                        "/usr/bin/env",
                        "rg",
                        "--json",
                        "-n",
                        "-S",
                        "--hidden",
                        "-f",
                        "-",
                        ".",
                    ],
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                },
            )

        hits = self._parse_stdout(completed.stdout)
        latency_ms = int((time.perf_counter() - start) * 1000)
        ok = completed.returncode in (0, 1)
        meta: dict[str, Any] = {
            "command": list(completed.args) if isinstance(completed.args, (list, tuple)) else completed.args,
            "exit_code": completed.returncode,
        }
        stderr = completed.stderr.strip()
        if stderr:
            meta["stderr"] = stderr
        return GrepResult(ok=ok, hits=hits, latency_ms=latency_ms, meta=meta)

    def describe(self) -> str:
        """Return a human-readable description."""
        return "Search files using ripgrep."

    def json_schema(self) -> dict:
        """Return the JSON schema for parameters."""
        return self.Param.model_json_schema()

    @staticmethod
    def _parse_stdout(stdout: str) -> list[GrepHit]:
        """Parse ripgrep JSON output and return a list of hits."""
        hits = []
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "match":
                continue
            data = payload.get("data", {})
            path_info = data.get("path", {})
            line_number = data.get("line_number")
            line_text = data.get("lines", {}).get("text", "")
            if not path_info or line_number is None:
                continue
            hits.append(
                GrepHit(
                    path=path_info.get("text", ""),
                    line=int(line_number),
                    text=line_text.rstrip("\n"),
                ),
            )
        return hits
