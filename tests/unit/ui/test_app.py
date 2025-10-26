"""Tests for the Streamlit UI helpers."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING

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
