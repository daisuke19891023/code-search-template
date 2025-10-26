"""Tests for the Streamlit UI helpers."""

from __future__ import annotations

import json

import pathlib

from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.parquet as pq

from codeagent_lab.experiments.store import ExperimentStore
from codeagent_lab.models import FlowTrace, ToolCall
from codeagent_lab.ui.app import build_flow_graph, load_run_records

if TYPE_CHECKING:
    from pathlib import Path


def _make_trace(run_id: str) -> FlowTrace:
    """Create a FlowTrace with two tool calls for testing."""
    return FlowTrace(
        run_id=run_id,
        metrics={"latency_ms": 125.0},
        calls=[
            ToolCall(name="grep", params={"pattern": "foo"}, result_summary={"hits": 3}, latency_ms=50),
            ToolCall(name="keyword", params={"query": "foo"}, result_summary={"score": 0.42}, latency_ms=75),
        ],
    )


def test_load_run_records_reads_logged_runs(tmp_path: Path) -> None:
    """Runs logged via the ExperimentStore can be loaded for display."""
    duckdb_path = tmp_path / "duckdb" / "runs.duckdb"
    parquet_root = tmp_path / "parquet"
    store = ExperimentStore(duckdb_path=duckdb_path, parquet_root=parquet_root)

    store.log_run(
        "run-a",
        params={"alpha": 0.1},
        metrics={"score": 0.9},
        trace=_make_trace("run-a"),
    )

    records = load_run_records(parquet_root)

    assert [record.run_id for record in records] == ["run-a"]
    record = records[0]
    assert record.metrics == {"score": 0.9}
    assert len(record.trace.calls) == 2


def test_build_flow_graph_generates_edges() -> None:
    """A flow graph renders sequential edges for tool calls."""
    trace = _make_trace("run-b")
    graph = build_flow_graph(trace)
    source = graph.source

    assert "step_1" in source
    assert "step_2" in source
    assert "step_1 -> step_2" in source
    assert json.dumps(trace.calls[0].result_summary, ensure_ascii=False) not in source


def test_load_run_records_skips_invalid_trace_rows(tmp_path: Path) -> None:
    """Rows with invalid trace payloads are skipped without raising errors."""
    parquet_root = tmp_path / "parquet"
    parquet_root.mkdir()

    valid_trace = _make_trace("valid-run")
    table = pa.Table.from_pylist(
        [
            {
                "run_id": "invalid-run",
                "params": json.dumps({}, ensure_ascii=False),
                "metrics": json.dumps({}, ensure_ascii=False),
                "trace": json.dumps({"run_id": "invalid-run", "calls": "oops"}, ensure_ascii=False),
            },
            {
                "run_id": "valid-run",
                "params": json.dumps({"alpha": 0.5}, ensure_ascii=False),
                "metrics": json.dumps({"score": 0.75}, ensure_ascii=False),
                "trace": json.dumps(valid_trace.model_dump(mode="json"), ensure_ascii=False),
            },
        ],
    )
    pq.write_table(table, str(parquet_root / "mixed.parquet"))

    records = load_run_records(parquet_root)

    assert [record.run_id for record in records] == ["valid-run"]


def test_load_run_records_handles_missing_files(monkeypatch: Any, tmp_path: Path) -> None:
    """Missing backing files do not cause load_run_records to raise errors."""
    parquet_root = tmp_path / "parquet"
    parquet_root.mkdir()

    trace = _make_trace("lost-run")
    table = pa.Table.from_pylist(
        [
            {
                "run_id": "lost-run",
                "params": json.dumps({}, ensure_ascii=False),
                "metrics": json.dumps({}, ensure_ascii=False),
                "trace": json.dumps(trace.model_dump(mode="json"), ensure_ascii=False),
            },
        ],
    )
    parquet_path = parquet_root / "lost.parquet"
    pq.write_table(table, str(parquet_path))

    original_stat = pathlib.Path.stat

    def _raising_stat(self: pathlib.Path, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - helper inside test
        if self == parquet_path:
            raise FileNotFoundError
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "stat", _raising_stat)

    records = load_run_records(parquet_root)

    assert records == []
