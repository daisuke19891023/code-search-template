"""Tests for the structlog-based logger configuration."""

from __future__ import annotations

import json

import pytest
import structlog

from codeagent_lab import logger as logger_module


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    """Reset structlog state before and after each test."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


def test_configure_emits_json(capfd: pytest.CaptureFixture[str]) -> None:
    """Configuring with ``json_out=True`` emits JSON log lines."""
    bound_logger = logger_module.configure(level="info", json_out=True)

    bound_logger.info("test-event", answer=42)

    captured = capfd.readouterr()
    payload = json.loads(captured.err.strip())

    assert payload["event"] == "test-event"
    assert payload["answer"] == 42
    assert payload["level"] == "info"


def test_configure_console_renderer(capfd: pytest.CaptureFixture[str]) -> None:
    """Disabling JSON output falls back to the console renderer."""
    bound_logger = logger_module.configure(level="debug", json_out=False)

    bound_logger.info("another-event", detail="value")

    captured = capfd.readouterr()
    stderr = captured.err.strip()

    assert "another-event" in stderr
    assert "detail" in stderr
