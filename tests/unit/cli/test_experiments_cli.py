"""Tests for the ``lab experiments`` CLI entry points."""

from __future__ import annotations

import pathlib

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from codeagent_lab.cli import experiments as experiments_cli


@pytest.fixture
def runner() -> CliRunner:
    """Return a CLI runner for invoking Typer commands."""
    return CliRunner()


def test_optimize_reports_settings_validation_error(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: pathlib.Path,
) -> None:
    """Settings validation failures surface a helpful error without a traceback."""
    dataset = pathlib.Path(tmp_path) / "dataset.json"
    dataset.write_text("{}")

    validation_error = ValidationError.from_exception_data(
        "Settings",
        [
            {
                "type": "value_error",
                "loc": ("optuna_storage",),
                "msg": "invalid storage url",
                "input": "bad",
                "ctx": {"error": ValueError("invalid storage url")},
            },
        ],
    )

    def _raise_settings() -> None:
        raise validation_error

    monkeypatch.setattr(experiments_cli, "Settings", _raise_settings)

    result = runner.invoke(experiments_cli.app, ["optimize", str(dataset)])

    assert result.exit_code == 1
    assert "Failed to load settings: 1 validation error for Settings" in result.output
    assert "invalid storage url" in result.output
    assert "Traceback" not in result.output
