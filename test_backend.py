"""Comprehensive Verification Test Script for ATLAS Prototype 1 Backend.

Tests:
1. Pydantic V2 Schemas & Enums
2. VectorMemoryStore (seed items, hybrid similarity search, insert)
3. TelemetryTracker (spans, tokens, latency, aggregation)
4. Workers (MaintenanceWorker, RDWorker, LocalState isolation)
5. TriageSupervisor (routing, memory injection, GlobalState merge)
6. MetaImproverAgent (offline self-improvement, token reduction, memory update)
7. FastAPI endpoints via ASGI protocol
"""

import asyncio
import json
from typing import Any, Optional
from urllib.parse import urlencode

from backend.app import app
from backend.memory import VectorMemoryStore
from backend.meta_improver import MetaImproverAgent
from backend.schemas import (
    DomainScope,
    ExecutionStatus,
    GlobalState,
    LocalState,
    MemoryItem,
    PromptOptimization,
    TaskPriority,
    TaskRequest,
    TaskResult,
    TaskType,
    TelemetryRecord,
)
from backend.telemetry import TelemetryTracker
from backend.triage import TriageSupervisor
from backend.workers import MaintenanceWorker, RDWorker


def test_schemas():
    """Verify all required Pydantic V2 schemas and enums."""
    print("\n--- 1. Testing Schemas & Enums ---")
    
    # Enums
    assert TaskType.BUG_FIX == "BUG_FIX"
    assert TaskType.FEATURE_IMPLEMENTATION == "FEATURE_IMPLEMENTATION"
    assert TaskType.EXPLORATION_RESEARCH == "EXPLORATION_RESEARCH"
    assert TaskType.REFACTORING == "REFACTORING"
    assert TaskType.DEPENDENCY_SECURITY == "DEPENDENCY_SECURITY"

    assert DomainScope.MAINTENANCE == "MAINTENANCE"
    assert DomainScope.RESEARCH_DEV == "RESEARCH_DEV"
    assert DomainScope.TRIAGE == "TRIAGE"

    assert TaskPriority.P0 == "P0"
    assert TaskPriority.P3 == "P3"

    assert ExecutionStatus.PENDING == "PENDING"
    assert ExecutionStatus.COMPLETED == "COMPLETED"

    # TaskRequest
    req = TaskRequest(
        title="Fix off-by-one error in reducer",
        description="Worker reducer drops the last element during batch aggregation.",
        task_type=TaskType.BUG_FIX,
        priority=TaskPriority.P1,
        code_snippet="for i in range(len(items)): process(items[i])",
    )
    assert req.task_id is not None
    assert req.priority == TaskPriority.P1

    # LocalState
    local = LocalState(
        task_id=req.task_id,
        worker_domain=DomainScope.MAINTENANCE,
        scratchpad_reasoning=["Step 1: Analyzed AST"],
        tool_calls=[{"tool": "read_file", "path": "test.py"}],
        raw_logs=["log line 1"],
        error_traces=["IndexError"],
    )
    assert len(local.scratchpad_reasoning) == 1
    assert len(local.tool_calls) == 1

    # GlobalState
    global_st = GlobalState(
        active_tasks={req.task_id: req},
        current_task_id=req.task_id,
    )
    assert req.task_id in global_st.active_tasks

    print("[PASS] Schemas & Enums verified successfully.")


def test_vector_memory():
    """Verify VectorMemoryStore indexing, hybrid similarity search, and seeding."""
    print("\n--- 2. Testing VectorMemoryStore ---")
    store = VectorMemoryStore(seed=True)
    all_items = store.list_all()
    assert len(all_items) >= 8, f"Expected >= 8 seeded items, found {len(all_items)}"

    # Search for off-by-one queue bug fix
    matches = store.search_memory("Fix off-by-one error in task queue reducer", domain=DomainScope.MAINTENANCE, top_k=2)
    assert len(matches) > 0
    top_item, score = matches[0]
    print(f"Top match for queue bug query: '{top_item.key}' with score: {score:.4f}")
    assert "queue" in top_item.key or "off_by_one" in top_item.key

    # Search for vector indexing research
    matches_rd = store.search_memory("Research vector indexing benchmarks pgvector HNSW", domain=DomainScope.RESEARCH_DEV, top_k=2)
    assert len(matches_rd) > 0
    top_rd, score_rd = matches_rd[0]
    print(f"Top match for research query: '{top_rd.key}' with score: {score_rd:.4f}")
    assert "vector_indexing" in top_rd.key

    # Test adding new memory
    new_item = store.add_memory(
        key="custom:perf_cache",
        content="LRU cache decorator applied to expensive database queries with 60s TTL.",
        domain=DomainScope.MAINTENANCE,
        tags=["cache", "lru", "perf"],
    )
    assert store.get_memory("custom:perf_cache") is not None
    print("[PASS] VectorMemoryStore verified successfully.")


def test_telemetry():
    """Verify TelemetryTracker span tracking, token accounting, and summary metrics."""
    print("\n--- 3. Testing TelemetryTracker ---")
    tracker = TelemetryTracker()

    with tracker.span("task-123", "triage", tokens_in=50) as span:
        span.add_tokens_out(25)
        span.set_metadata("step", "classify")

    with tracker.span("task-123", "worker_maintenance", tokens_in=150) as span:
        span.add_tokens_out(100)
        span.set_metadata("patch", "unified_diff")

    traces = tracker.get_traces("task-123")
    assert len(traces) == 2
    assert traces[0].node_name == "triage"
    assert traces[0].tokens_in == 50
    assert traces[0].tokens_out == 25
    assert traces[0].cost_usd > 0
    assert traces[0].duration_ms >= 0

    metrics = tracker.get_summary_metrics()
    assert metrics["total_traces"] == 2
    assert metrics["total_tokens_in"] == 200
    assert metrics["total_tokens_out"] == 125
    assert metrics["total_tokens"] == 325
    assert metrics["total_cost_usd"] > 0
    assert "triage" in metrics["node_breakdown"]
    assert "worker_maintenance" in metrics["node_breakdown"]
    print(f"Metrics: {metrics['total_tokens']} tokens, ${metrics['total_cost_usd']:.6f} cost, {metrics['avg_latency_ms']:.2f}ms avg latency")
    print("[PASS] TelemetryTracker verified successfully.")


def test_workers_and_triage():
    """Verify Workers, TriageSupervisor routing, and LocalState isolation."""
    print("\n--- 4. Testing Workers, Triage & Isolation ---")
    store = VectorMemoryStore(seed=True)
    tracker = TelemetryTracker()
    supervisor = TriageSupervisor(memory_store=store, telemetry_tracker=tracker)

    # Test 1: Maintenance Worker Dispatch (Bug Fix)
    task_bug = TaskRequest(
        title="Fix off-by-one loop in batch processor",
        description="Loop overshoots array boundary by 1 causing IndexError.",
        task_type=TaskType.BUG_FIX,
        priority=TaskPriority.P0,
        code_snippet="for i in range(len(tasks)): process(tasks[i])",
    )
    result_bug = supervisor.run_task(task_bug)

    assert result_bug.status == ExecutionStatus.COMPLETED
    assert result_bug.assigned_worker == "MaintenanceWorker"
    assert result_bug.code_patch is not None
    assert "--- a/" in result_bug.code_patch
    assert len(result_bug.telemetry_records) >= 3  # triage, memory_retrieval, worker_maintenance

    # Inspect LocalState isolation
    local_state_bug = supervisor.get_local_state(task_bug.task_id)
    assert local_state_bug is not None
    assert len(local_state_bug.scratchpad_reasoning) > 0
    assert len(local_state_bug.tool_calls) > 0
    assert len(local_state_bug.error_traces) > 0  # Demonstrates isolated error retry loop

    # Check that supervisor's GlobalState does NOT contain worker's private scratchpad or raw logs
    global_completed = supervisor.global_state.completed_tasks[task_bug.task_id]
    assert "scratchpad_reasoning" not in global_completed
    assert "error_traces" not in global_completed
    assert "tool_calls" not in global_completed
    print("Verified LocalState isolation: scratchpad reasoning and error retry loops kept private from GlobalState.")

    # Test 2: R&D Worker Dispatch (Exploration Research)
    task_rd = TaskRequest(
        title="Research vector indexing benchmarks for hybrid search",
        description="Benchmark HNSW vs IVFFlat for multi-tenant pgvector deployment.",
        task_type=TaskType.EXPLORATION_RESEARCH,
        priority=TaskPriority.P2,
    )
    result_rd = supervisor.run_task(task_rd)

    assert result_rd.status == ExecutionStatus.COMPLETED
    assert result_rd.assigned_worker == "RDWorker"
    assert "HNSW" in result_rd.result_summary or "feasibility" in result_rd.result_summary

    local_state_rd = supervisor.get_local_state(task_rd.task_id)
    assert local_state_rd is not None
    assert len(local_state_rd.hypotheses) >= 2
    assert len(local_state_rd.scratchpad_reasoning) >= 3

    print(f"R&D Worker verified: Hypotheses evaluated: {len(local_state_rd.hypotheses)}")
    print("[PASS] Workers, Triage, and State Isolation verified successfully.")


def test_meta_improver():
    """Verify MetaImproverAgent offline self-improvement and prompt optimization."""
    print("\n--- 5. Testing MetaImproverAgent ---")
    store = VectorMemoryStore(seed=True)
    tracker = TelemetryTracker()

    # Pre-populate some telemetry traces
    with tracker.span("task-1", "worker_maintenance", tokens_in=500) as span:
        span.add_tokens_out(300)

    improver = MetaImproverAgent(memory_store=store, telemetry_tracker=tracker)
    optimizations = improver.run_improvement_cycle()

    assert len(optimizations) == 3
    for opt in optimizations:
        print(f"Optimized '{opt.prompt_id}' ({opt.target_agent}): {opt.token_reduction_pct}% reduction")
        assert opt.token_reduction_pct > 0
        assert opt.optimized_prompt != opt.original_prompt

        # Verify updated in memory store
        updated_item = store.get_memory(opt.prompt_id)
        assert updated_item is not None
        assert updated_item.content == opt.optimized_prompt
        assert "optimized_v2" in updated_item.tags

    print("[PASS] MetaImproverAgent verified successfully.")


async def _run_asgi_request(
    app: Any,
    method: str,
    path: str,
    body: Optional[dict[str, Any]] = None,
    query_params: Optional[dict[str, Any]] = None,
) -> tuple[int, dict[str, Any] | str]:
    """Execute ASGI HTTP request directly against the FastAPI app instance."""
    query_string = urlencode(query_params or {}).encode("utf-8")
    body_bytes = json.dumps(body).encode("utf-8") if body else b""

    status_code = 500
    response_headers = []
    response_body = bytearray()

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    async def send(message):
        nonlocal status_code, response_headers, response_body
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body_bytes)).encode("utf-8")),
    ]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "app": app,
    }

    await app(scope, receive, send)

    try:
        parsed_body = json.loads(response_body.decode("utf-8"))
    except Exception:
        parsed_body = response_body.decode("utf-8")

    return status_code, parsed_body


async def test_fastapi_endpoints():
    """Verify all FastAPI REST endpoints using ASGI requests."""
    print("\n--- 6. Testing FastAPI Endpoints (ASGI) ---")

    # 1. GET /api/memory
    status, res = await _run_asgi_request(app, "GET", "/api/memory")
    assert status == 200
    assert "items" in res
    assert res["total_items"] >= 8
    print(f"GET /api/memory -> Status {status}, total_items: {res['total_items']}")

    # 2. POST /api/memory
    new_mem = {
        "key": "test:endpoint_doc",
        "content": "Documentation for REST API endpoints and state models.",
        "domain": "RESEARCH_DEV",
        "tags": ["docs", "api"],
    }
    status, res = await _run_asgi_request(app, "POST", "/api/memory", body=new_mem)
    assert status == 200
    assert res["key"] == "test:endpoint_doc"
    print(f"POST /api/memory -> Status {status}, stored key: {res['key']}")

    # 3. GET /api/memory with query search
    status, res = await _run_asgi_request(app, "GET", "/api/memory", query_params={"query": "off-by-one queue"})
    assert status == 200
    assert "results" in res
    assert len(res["results"]) > 0
    print(f"GET /api/memory?query=... -> Status {status}, found {len(res['results'])} matches")

    # 4. POST /api/tasks
    task_payload = {
        "title": "Patch off-by-one exception in task dispatcher",
        "description": "Ensure boundary conditions are respected when queue is at maximum capacity.",
        "task_type": "BUG_FIX",
        "priority": "P1",
    }
    status, res = await _run_asgi_request(app, "POST", "/api/tasks", body=task_payload)
    assert status == 200
    task_id = res["task_id"]
    assert res["status"] == "COMPLETED"
    assert res["assigned_worker"] == "MaintenanceWorker"
    assert res["code_patch"] is not None
    print(f"POST /api/tasks -> Status {status}, task_id: {task_id}, worker: {res['assigned_worker']}")

    # 5. GET /api/tasks
    status, res = await _run_asgi_request(app, "GET", "/api/tasks")
    assert status == 200
    assert isinstance(res, list)
    assert len(res) >= 1
    print(f"GET /api/tasks -> Status {status}, completed tasks: {len(res)}")

    # 6. GET /api/tasks/{task_id}/state
    status, res = await _run_asgi_request(app, "GET", f"/api/tasks/{task_id}/state")
    assert status == 200
    assert res["isolation_verified"] is True
    assert res["global_state"] is not None
    assert res["local_state"] is not None
    assert "scratchpad_reasoning" in res["local_state"]
    print(f"GET /api/tasks/{task_id}/state -> Status {status}, isolation_verified: {res['isolation_verified']}")

    # 7. GET /api/telemetry
    status, res = await _run_asgi_request(app, "GET", "/api/telemetry")
    assert status == 200
    assert "summary" in res
    assert "traces" in res
    assert res["summary"]["total_traces"] > 0
    print(f"GET /api/telemetry -> Status {status}, total traces: {res['summary']['total_traces']}")

    # 8. POST /api/meta-improve
    status, res = await _run_asgi_request(app, "POST", "/api/meta-improve")
    assert status == 200
    assert res["status"] == "success"
    assert res["optimizations_count"] >= 3
    print(f"POST /api/meta-improve -> Status {status}, optimizations generated: {res['optimizations_count']}")

    # 9. GET / (Static files frontend)
    status, res = await _run_asgi_request(app, "GET", "/")
    assert status == 200
    assert "ATLAS Prototype 1" in str(res)
    print(f"GET / (Static Frontend) -> Status {status}, verified HTML served.")

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")


def main():
    test_schemas()
    test_vector_memory()
    test_telemetry()
    test_workers_and_triage()
    test_meta_improver()
    asyncio.run(test_fastapi_endpoints())


if __name__ == "__main__":
    main()
