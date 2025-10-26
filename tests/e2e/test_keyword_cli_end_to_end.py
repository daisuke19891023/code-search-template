"""End-to-end tests exercising the Typer CLI with real tool implementations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from codeagent_lab.cli import tools as tools_cli


if TYPE_CHECKING:
    from pathlib import Path


def test_keyword_tool_via_cli(tmp_path: Path) -> None:
    """Running the keyword tool through the CLI returns ranked hits."""
    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / "notes.txt").write_text("Keyword driven search tooling.\n", encoding="utf-8")

    runner = CliRunner()
    env = {
        "LAB_SEMANTIC_EMBED_BACKEND": "none",
        "LAB_DATA_ROOT": str(tmp_path / "data"),
        "LAB_DUCKDB_PATH": str(tmp_path / "data" / "experiments.duckdb"),
        "LAB_PARQUET_ROOT": str(tmp_path / "parquet"),
        "LAB_INDEX_ROOT": str(tmp_path / "indexes"),
    }
    params = {"query": "keyword", "root": str(project_root), "topk": 5}

    result = runner.invoke(
        tools_cli.app,
        ["run", "--domain", "keyword", "--params-json", json.dumps(params)],
        env=env,
    )

    assert result.exit_code == 0, result.stderr

    stdout = result.stdout.strip()
    if stdout.startswith('{"embed_backend"'):
        _, _, stdout = stdout.partition("\n")

    payload = json.loads(stdout)

    assert payload["ok"] is True
    assert payload["hits"], payload
    top_hit = payload["hits"][0]
    assert top_hit["path"] == "notes.txt"
    assert isinstance(top_hit["score"], float)
