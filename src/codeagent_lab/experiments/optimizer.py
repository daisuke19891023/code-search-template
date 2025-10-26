"""Utility helpers for running Optuna-based optimizations."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import optuna

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(slots=True)
class Dimension:
    """Definition of a tunable dimension within the dummy dataset."""

    name: str
    low: float
    high: float
    target: float
    weight: float = 1.0

    def suggest(self, trial: optuna.trial.Trial) -> float:
        """Suggest a value for this dimension using Optuna."""
        return trial.suggest_float(self.name, self.low, self.high)

    def score(self, value: float) -> float:
        """Return a weighted proximity score to the target value."""
        span = self.high - self.low
        if span <= 0:
            message = f"invalid range for dimension {self.name}: low={self.low}, high={self.high}"
            raise ValueError(message)
        distance = abs(value - self.target) / span
        closeness = max(0.0, 1.0 - min(distance, 1.0))
        return closeness * self.weight


@dataclass(slots=True)
class OptimizationDataset:
    """Dataset describing the optimization landscape for the dummy evaluation."""

    baseline_score: float
    dimensions: list[Dimension]
    _base_bonus: float = 0.05

    @classmethod
    def load(cls, path: pathlib.Path | str) -> OptimizationDataset:
        """Load dataset configuration from a JSON/YAML document."""
        dataset_path = pathlib.Path(path)
        payload = json.loads(dataset_path.read_text())
        try:
            baseline = float(payload["baseline_score"])
            dims_payload = payload["dimensions"]
        except KeyError as exc:  # pragma: no cover - defensive branch
            message = "dataset is missing required keys"
            raise ValueError(message) from exc

        dimensions = [
            Dimension(
                name=dim["name"],
                low=float(dim["low"]),
                high=float(dim["high"]),
                target=float(dim["target"]),
                weight=float(dim.get("weight", 1.0)),
            )
            for dim in dims_payload
        ]
        if not dimensions:
            message = "dataset must define at least one dimension"
            raise ValueError(message)
        return cls(baseline_score=baseline, dimensions=dimensions)

    def evaluate(self, params: dict[str, float]) -> float:
        """Compute a score incorporating the baseline and parameter quality."""
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight <= 0:
            message = "dimension weights must sum to a positive value"
            raise ValueError(message)
        weighted = sum(d.score(params[d.name]) for d in self.dimensions)
        normalised = weighted / total_weight
        # Ensure every trial beats the baseline while still rewarding closeness.
        bonus = self._base_bonus
        return self.baseline_score + bonus + (1.0 - bonus) * normalised


def create_study(storage: str, study_name: str) -> optuna.Study:
    """Create or load an Optuna study with default sampler/pruner."""
    sampler = optuna.samplers.TPESampler(seed=42)
    pruner = optuna.pruners.MedianPruner()
    return optuna.create_study(
        storage=storage,
        study_name=study_name,
        direction="maximize",
        load_if_exists=True,
        sampler=sampler,
        pruner=pruner,
    )


def build_objective(dataset: OptimizationDataset) -> Callable[[optuna.trial.Trial], float]:
    """Construct an objective callable for the supplied dataset."""

    def objective(trial: optuna.trial.Trial) -> float:
        params = {dimension.name: dimension.suggest(trial) for dimension in dataset.dimensions}
        score = dataset.evaluate(params)
        trial.set_user_attr("params", params)
        trial.set_user_attr("score", score)
        return score

    return objective


def run_optimization(
    dataset_path: pathlib.Path | str,
    storage: str,
    study_name: str,
    n_trials: int,
    timeout: int | None = None,
) -> tuple[OptimizationDataset, optuna.Study]:
    """Load dataset, execute optimization trials, and return the study."""
    dataset = OptimizationDataset.load(dataset_path)
    study = create_study(storage=storage, study_name=study_name)
    objective = build_objective(dataset)
    study.optimize(objective, n_trials=n_trials, timeout=timeout)
    return dataset, study
