"""Optuna optimization scaffold."""

from __future__ import annotations

import optuna


def create_study(storage: str, study_name: str) -> optuna.Study:
    """Create or load an Optuna study."""
    return optuna.create_study(storage=storage, study_name=study_name, direction="maximize")
