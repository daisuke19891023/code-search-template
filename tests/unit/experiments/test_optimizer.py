"""Tests covering the Optuna optimizer integration."""

from __future__ import annotations

import json
import pathlib

import optuna

from codeagent_lab.experiments import optimizer


def _write_dataset(path: pathlib.Path) -> pathlib.Path:
    """Persist a dummy optimization dataset to disk."""
    dataset_path = pathlib.Path(path)
    payload = {
        "baseline_score": 0.3,
        "dimensions": [
            {"name": "alpha", "low": 0.0, "high": 1.0, "target": 0.75, "weight": 0.7},
            {"name": "beta", "low": 0.0, "high": 1.0, "target": 0.25, "weight": 0.3},
        ],
    }
    dataset_path.write_text(json.dumps(payload))
    return dataset_path


def test_create_study_configures_sampler_and_pruner(tmp_path: pathlib.Path) -> None:
    """Studies use TPE sampling and the median pruner by default."""
    storage = f"sqlite:///{tmp_path / 'study.db'}"
    study = optimizer.create_study(storage=storage, study_name="unit-test")

    assert isinstance(study.sampler, optuna.samplers.TPESampler)
    assert isinstance(study.pruner, optuna.pruners.MedianPruner)


def test_run_optimization_improves_baseline(tmp_path: pathlib.Path) -> None:
    """Executing the optimization yields a best value higher than the baseline."""
    dataset_path = _write_dataset(tmp_path / "dataset.json")
    storage = f"sqlite:///{tmp_path / 'optuna.db'}"

    dataset_config, study = optimizer.run_optimization(
        dataset_path=dataset_path,
        storage=storage,
        study_name="unit-test",
        n_trials=8,
        timeout=None,
    )

    assert study.best_value is not None
    assert study.best_value > dataset_config.baseline_score
