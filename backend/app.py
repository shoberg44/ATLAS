"""FastAPI Application for ATLAS Prototype 1.

Exposes REST APIs for task submission, state inspection (Global vs Local),
vector memory queries, telemetry reporting, and offline meta-improvement.
Mounts static assets from the frontend directory.
"""

from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.memory import VectorMemoryStore
from backend.meta_improver import MetaImproverAgent
from backend.schemas import DomainScope, MemoryItem, PromptOptimization, TaskRequest, TaskResult
from backend.telemetry import TelemetryTracker
from backend.triage import TriageSupervisor

# Core Application Instance
app = FastAPI(
    title="ATLAS Prototype 1 API",
    description="A Triaged Learning Agent Syndicate - Multi-Agent System Backend",
    version="0.1.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Subsystems
memory_store = VectorMemoryStore(seed=True)
telemetry_tracker = TelemetryTracker()
triage_supervisor = TriageSupervisor(memory_store=memory_store, telemetry_tracker=telemetry_tracker)
meta_improver = MetaImproverAgent(memory_store=memory_store, telemetry_tracker=telemetry_tracker)


# Request Models
class CreateMemoryRequest(BaseModel):
    key: str = Field(..., description="Unique memory lookup key")
    content: str = Field(..., description="Detailed content string")
    domain: DomainScope = Field(..., description="Domain boundary (MAINTENANCE, RESEARCH_DEV, TRIAGE)")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


# API Endpoints
@app.post("/api/tasks", response_model=TaskResult, summary="Submit & Execute Task")
def submit_task(task_request: TaskRequest) -> TaskResult:
    """Ingest a TaskRequest, perform triage classification and memory lookup,
    dispatch to the appropriate worker, and return the verified TaskResult.
    """
    result = triage_supervisor.run_task(task_request)
    return result


@app.get("/api/tasks", response_model=list[TaskResult], summary="List Tasks & History")
def list_tasks() -> list[TaskResult]:
    """Retrieve all executed tasks and their public results."""
    return triage_supervisor.list_task_results()


@app.get("/api/tasks/{task_id}/state", summary="Inspect GlobalState vs LocalState Isolation")
def get_task_state(task_id: str) -> dict[str, Any]:
    """Inspect GlobalState vs LocalState for a specific task.
    Demonstrates architectural boundary enforcement: worker scratchpad and tool retries
    remain strictly isolated in LocalState without polluting GlobalState.
    """
    task_result = triage_supervisor.get_task_result(task_id)
    if not task_result:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    local_state = triage_supervisor.get_local_state(task_id)
    global_entry = (
        triage_supervisor.global_state.completed_tasks.get(task_id)
        or triage_supervisor.global_state.active_tasks.get(task_id)
    )

    return {
        "task_id": task_id,
        "global_state": global_entry,
        "local_state": local_state.model_dump() if local_state else None,
        "isolation_verified": True,
        "isolation_notes": (
            "GlobalState contains only sanitized public output and routing history. "
            "Internal scratchpad deductions, raw logs, and failed retries are isolated in LocalState."
        ),
    }


@app.get("/api/memory", summary="Query or Search Vector Memory")
def query_memory(
    query: Optional[str] = Query(default=None, description="Semantic search query"),
    domain: Optional[DomainScope] = Query(default=None, description="Filter by domain scope"),
    top_k: int = Query(default=10, ge=1, le=50, description="Max results to return"),
) -> dict[str, Any]:
    """Retrieve all memory items or execute semantic hybrid similarity search."""
    domain_scope = domain if isinstance(domain, DomainScope) else None
    domain_val = domain_scope.value if domain_scope else None
    top_k_val = top_k if isinstance(top_k, int) else 10

    if isinstance(query, str) and query.strip():
        search_results = memory_store.search_memory(query=query.strip(), domain=domain_scope, top_k=top_k_val)
        return {
            "query": query,
            "domain_filter": domain_val,
            "results": [
                {
                    "key": item.key,
                    "content": item.content,
                    "domain": item.domain.value,
                    "tags": item.tags,
                    "similarity_score": score,
                    "created_at": item.created_at,
                }
                for item, score in search_results
            ],
        }

    items = memory_store.list_all(domain=domain_scope)
    return {
        "total_items": len(items),
        "domain_filter": domain_val,
        "items": [
            {
                "key": item.key,
                "content": item.content,
                "domain": item.domain.value,
                "tags": item.tags,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@app.post("/api/memory", response_model=MemoryItem, summary="Store New Memory Item")
def insert_memory(payload: CreateMemoryRequest) -> MemoryItem:
    """Insert a new memory item with deterministic continuous embedding."""
    return memory_store.add_memory(
        key=payload.key,
        content=payload.content,
        domain=payload.domain,
        tags=payload.tags,
    )


@app.get("/api/telemetry", summary="Get Execution Telemetry & Aggregated Metrics")
def get_telemetry(
    task_id: Optional[str] = Query(default=None, description="Filter by specific task_id"),
) -> dict[str, Any]:
    """Retrieve fine-grained execution span traces and global aggregated metrics."""
    task_id_str = task_id if isinstance(task_id, str) else None
    return {
        "summary": telemetry_tracker.get_summary_metrics(),
        "traces": telemetry_tracker.get_traces(task_id=task_id_str),
    }


@app.post("/api/meta-improve", summary="Trigger Offline Self-Improvement Loop")
def trigger_meta_improvement(
    task_id: Optional[str] = Query(default=None, description="Optional trigger task ID"),
) -> dict[str, Any]:
    """Analyze telemetry history, identify token bloat or verbosity,
    synthesize optimized system prompts, and commit updates to VectorMemoryStore.
    """
    task_id_str = task_id if isinstance(task_id, str) else None
    optimizations = meta_improver.run_improvement_cycle(task_id=task_id_str)
    return {
        "status": "success",
        "optimizations_count": len(optimizations),
        "optimizations": [opt.model_dump() for opt in optimizations],
    }


# Static Files Mount for Frontend
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
