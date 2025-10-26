"""Helpers for filtering repository paths within a root directory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def resolve_within_root(resolved_root: Path, candidate: Path) -> Path | None:
    """Return ``candidate`` resolved if it stays within ``resolved_root``.

    Symlinks are ignored and any path resolving outside of ``resolved_root`` is
    skipped. ``None`` is returned whenever the candidate should be ignored.
    """
    try:
        if candidate.is_symlink():
            return None
    except OSError:
        return None

    try:
        resolved = candidate.resolve()
    except OSError:
        return None

    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None

    return resolved
