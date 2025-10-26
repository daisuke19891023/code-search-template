"""Tests for the experiment store."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import duckdb
import pyarrow.parquet as pq

from codeagent_lab.experiments.store import ExperimentStore
from codeagent_lab.models import FlowTrace

if TYPE_CHECKING:
    import pathlib


def _make_trace(run_id: str) -> FlowTrace:
    """Create a simple flow trace for testing."""
    return FlowTrace(run_id=run_id, metrics={"latency_ms": 42.0})


def test_log_run_appends_to_parquet_and_duckdb(tmp_path: pathlib.Path) -> None:
    """Ensure that log_run appends rows and updates DuckDB."""
    duckdb_path = tmp_path / "db" / "runs.duckdb"
    parquet_root = tmp_path / "parquet"
    store = ExperimentStore(duckdb_path=duckdb_path, parquet_root=parquet_root)

    store.log_run("run-1", {"alpha": 1}, {"score": 0.1}, _make_trace("run-1"))
    store.log_run("run-2", {"alpha": 2}, {"score": 0.2}, _make_trace("run-2"))

    pq_files = sorted(parquet_root.glob("*.parquet"))
    assert len(pq_files) == 2
    rows: list[dict[str, object]] = []
    for path in pq_files:
        table = pq.read_table(path)
        rows.extend(table.to_pylist())

    rows.sort(key=lambda item: item["run_id"])
    assert [row["run_id"] for row in rows] == ["run-1", "run-2"]

    metrics = [json.loads(row["metrics"]) for row in rows]
    assert metrics == [{"score": 0.1}, {"score": 0.2}]

    with duckdb.connect(duckdb_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        assert count == 2
