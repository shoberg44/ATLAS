"""Telemetry and Observability Layer for ATLAS Prototype 1.

Tracks node execution spans, computes token consumption (in/out),
measures latency, correlates agent/tool attribution, and calculates USD costs.
"""

from contextlib import contextmanager
import time
from typing import Any, Generator, Optional
import uuid

from backend.schemas import TelemetryRecord


# Standard pricing per token (e.g. Claude 3.5 Sonnet / GPT-4o reference rates)
COST_PER_INPUT_TOKEN = 0.000003   # $3.00 per 1M input tokens
COST_PER_OUTPUT_TOKEN = 0.000015  # $15.00 per 1M output tokens


def estimate_tokens(text: Optional[str]) -> int:
    """Heuristic token estimator (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text.strip()) // 4)


class SpanContext:
    """Active span context for timing and token accounting."""

    def __init__(self, tracker: "TelemetryTracker", task_id: str, node_name: str):
        self.tracker = tracker
        self.task_id = task_id
        self.node_name = node_name
        self.trace_id = str(uuid.uuid4())
        self.tokens_in = 0
        self.tokens_out = 0
        self.metadata: dict[str, Any] = {}
        self.start_time: float = 0.0

    def add_tokens_in(self, count: int) -> None:
        self.tokens_in += count

    def add_tokens_out(self, count: int) -> None:
        self.tokens_out += count

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value


class TelemetryTracker:
    """In-memory telemetry tracker and span registry."""

    def __init__(self):
        self._records: list[TelemetryRecord] = []

    @contextmanager
    def span(
        self,
        task_id: str,
        node_name: str,
        tokens_in: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Generator[SpanContext, None, None]:
        """Context manager to measure execution latency and record token spans."""
        ctx = SpanContext(self, task_id, node_name)
        ctx.tokens_in = tokens_in
        if metadata:
            ctx.metadata.update(metadata)

        ctx.start_time = time.perf_counter()
        try:
            yield ctx
        finally:
            duration_ms = (time.perf_counter() - ctx.start_time) * 1000.0
            cost_usd = (ctx.tokens_in * COST_PER_INPUT_TOKEN) + (ctx.tokens_out * COST_PER_OUTPUT_TOKEN)

            record = TelemetryRecord(
                trace_id=ctx.trace_id,
                task_id=ctx.task_id,
                node_name=ctx.node_name,
                duration_ms=round(duration_ms, 2),
                tokens_in=ctx.tokens_in,
                tokens_out=ctx.tokens_out,
                cost_usd=round(cost_usd, 6),
                metadata=ctx.metadata,
            )
            self._records.append(record)

    def record_manual(
        self,
        task_id: str,
        node_name: str,
        duration_ms: float,
        tokens_in: int,
        tokens_out: int,
        metadata: Optional[dict[str, Any]] = None,
    ) -> TelemetryRecord:
        """Manually record a completed execution span."""
        cost_usd = (tokens_in * COST_PER_INPUT_TOKEN) + (tokens_out * COST_PER_OUTPUT_TOKEN)
        record = TelemetryRecord(
            task_id=task_id,
            node_name=node_name,
            duration_ms=round(duration_ms, 2),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost_usd, 6),
            metadata=metadata or {},
        )
        self._records.append(record)
        return record

    def get_traces(
        self,
        task_id: Optional[str] = None,
        node_name: Optional[str] = None,
    ) -> list[TelemetryRecord]:
        """Retrieve traces, optionally filtered by task_id or node_name."""
        results = self._records
        if task_id:
            results = [r for r in results if r.task_id == task_id]
        if node_name:
            results = [r for r in results if r.node_name == node_name]
        return results

    def get_summary_metrics(self) -> dict[str, Any]:
        """Compute aggregated metrics across all recorded execution spans."""
        if not self._records:
            return {
                "total_traces": 0,
                "total_tasks": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "node_breakdown": {},
            }

        total_tokens_in = sum(r.tokens_in for r in self._records)
        total_tokens_out = sum(r.tokens_out for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)
        total_duration = sum(r.duration_ms for r in self._records)
        unique_tasks = len(set(r.task_id for r in self._records))

        # Node-by-node breakdown
        node_breakdown: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.node_name not in node_breakdown:
                node_breakdown[r.node_name] = {
                    "count": 0,
                    "total_duration_ms": 0.0,
                    "total_tokens_in": 0,
                    "total_tokens_out": 0,
                    "total_cost_usd": 0.0,
                }
            nb = node_breakdown[r.node_name]
            nb["count"] += 1
            nb["total_duration_ms"] += r.duration_ms
            nb["total_tokens_in"] += r.tokens_in
            nb["total_tokens_out"] += r.tokens_out
            nb["total_cost_usd"] += r.cost_usd

        # Calculate averages per node
        for node, data in node_breakdown.items():
            count = data["count"]
            data["avg_latency_ms"] = round(data["total_duration_ms"] / count, 2)
            data["total_duration_ms"] = round(data["total_duration_ms"], 2)
            data["total_cost_usd"] = round(data["total_cost_usd"], 6)

        return {
            "total_traces": len(self._records),
            "total_tasks": unique_tasks,
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_tokens": total_tokens_in + total_tokens_out,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(total_duration / len(self._records), 2),
            "node_breakdown": node_breakdown,
        }
