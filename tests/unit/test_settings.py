"""Tests covering the application settings model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from codeagent_lab.settings import Settings


if TYPE_CHECKING:
    import pytest


def test_settings_have_reasonable_defaults() -> None:
    """The settings object exposes the documented default values."""
    settings = Settings()

    assert settings.log_level == "INFO"
    assert settings.semantic_embed_backend == "openai"
    assert settings.data_root == Path(".labdata")
    assert settings.duckdb_path == Path(".labdata/experiments.duckdb")
    assert settings.parquet_root == Path(".labdata/parquet")


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Environment variables prefixed with ``LAB_`` override defaults."""
    monkeypatch.setenv("LAB_LOG_LEVEL", "debug")
    monkeypatch.setenv("LAB_DATA_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("LAB_PARQUET_ROOT", str(tmp_path / "parquet"))

    settings = Settings()

    assert settings.log_level == "debug"
    assert settings.data_root == tmp_path / "storage"
    assert settings.parquet_root == tmp_path / "parquet"
