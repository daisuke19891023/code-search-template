"""CLI integration tests for the tool runner."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from codeagent_lab.cli.tools import app

if TYPE_CHECKING:
    from pathlib import Path
    import pytest


def test_cli_run_invokes_ripgrep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running the CLI produces JSON hits for ripgrep."""
    (tmp_path / "notes.txt").write_text("TODO: finish task\n")

    data_root = tmp_path / "data"
    monkeypatch.setenv("LAB_DATA_ROOT", str(data_root))
    monkeypatch.setenv("LAB_PARQUET_ROOT", str(data_root / "parquet"))
    monkeypatch.setenv("LAB_DUCKDB_PATH", str(data_root / "experiments.duckdb"))
    monkeypatch.setenv("LAB_INDEX_ROOT", str(data_root / "indexes"))

    runner = CliRunner()
    params = json.dumps({"pattern": "TODO", "root": str(tmp_path)})

    result = runner.invoke(app, ["run", "grep", params])

    assert result.exit_code == 0
    _, json_blob = result.stdout.split("\n", 1)
    payload = json.loads(json_blob)
    assert payload["hits"], result.stdout
    assert payload["meta"]["exit_code"] == 0
