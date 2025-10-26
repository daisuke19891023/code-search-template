"""Structured logging configuration for the laboratory."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure(level: str = "INFO", json_out: bool = True) -> structlog.BoundLogger:
    """Configure structlog for the application and return a bound logger."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stderr,
        force=True,
    )
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer() if json_out else structlog.dev.ConsoleRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()
