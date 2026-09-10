"""Pydantic V2 Schemas for ATLAS Prototype 1.

Defines all core state models, enums, task requests, responses,
telemetry records, and memory representations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TaskType(str, Enum):
    """Deterministic operational categories for incoming tasks."""
    BUG_FIX = "BUG_FIX"
    FEATURE_IMPLEMENTATION = "FEATURE_IMPLEMENTATION"
    EXPLORATION_RESEARCH = "EXPLORATION_RESEARCH"
    REFACTORING = "REFACTORING"
    DEPENDENCY_SECURITY = "DEPENDENCY_SECURITY"


class DomainScope(str, Enum):
    """Domain boundaries preventing cross-contamination of execution environments."""
    MAINTENANCE = "MAINTENANCE"
    RESEARCH_DEV = "RESEARCH_DEV"
    TRIAGE = "TRIAGE"


class TaskPriority(str, Enum):
    """Task urgency levels."""
    P0 = "P0"  # Critical / Blocker
    P1 = "P1"  # High
    P2 = "P2"  # Medium
    P3 = "P3"  # Low / Backlog


class ExecutionStatus(str, Enum):
    """Lifecycle states tracked in the global state machine."""
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskRequest(BaseModel):
    """Ingested and normalized user task specification."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., description="Concise human-readable task summary")
    description: str = Field(..., description="Detailed narrative describing desired outcome")
    task_type: TaskType = Field(..., description="Classification category for execution")
    priority: TaskPriority = Field(default=TaskPriority.P2, description="Task urgency level")
    code_snippet: Optional[str] = Field(default=None, description="Optional target code snippet or stack trace")
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Guardrails (e.g. timeout_seconds, allowed_paths, max_token_budget, require_human_approval)"
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="ignore")


class LocalState(BaseModel):
    """Isolated worker execution scratchpad.
    
    Houses intermediate thoughts, raw tool payloads, shell output,
    and error traces. Strictly isolated from the supervisor context.
    """
    task_id: str
    worker_domain: DomainScope
    scratchpad_reasoning: list[str] = Field(default_factory=list, description="Step-by-step worker deductions")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, description="Raw tool invocation history")
    raw_logs: list[str] = Field(default_factory=list, description="Unfiltered execution and shell logs")
    error_traces: list[str] = Field(default_factory=list, description="Failing runtime traces or test exceptions")
    hypotheses: list[dict[str, Any]] = Field(default_factory=list, description="Formulated hypotheses and test results")
    candidate_diffs: list[str] = Field(default_factory=list, description="Intermediate diff patches evaluated")

    model_config = ConfigDict(extra="ignore")


class GlobalState(BaseModel):
    """Minimalist, high-level task state visible to the Triage Supervisor."""
    active_tasks: dict[str, Any] = Field(default_factory=dict, description="Active task requests indexed by task_id")
    completed_tasks: dict[str, Any] = Field(default_factory=dict, description="Finished tasks indexed by task_id")
    current_task_id: Optional[str] = Field(default=None, description="Currently dispatched task ID")
    final_output: Optional[dict[str, Any]] = Field(default=None, description="Public consolidated output of latest task")
    routing_history: list[dict[str, Any]] = Field(default_factory=list, description="Triage routing decisions log")

    model_config = ConfigDict(extra="ignore")


class TelemetryRecord(BaseModel):
    """Granular execution span telemetry capturing latency, token usage, and cost."""
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    node_name: str
    duration_ms: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PromptOptimization(BaseModel):
    """Self-improvement mutation proposed by the offline meta-improver."""
    prompt_id: str
    target_agent: str
    original_prompt: str
    optimized_prompt: str
    rationale: str
    token_reduction_pct: float

    model_config = ConfigDict(extra="ignore")


class TaskResult(BaseModel):
    """Final public output and audit trail returned to client."""
    task_id: str
    status: ExecutionStatus
    assigned_worker: str
    result_summary: str
    code_patch: Optional[str] = Field(default=None, description="Unified diff patch if applicable")
    telemetry_records: list[TelemetryRecord] = Field(default_factory=list)
    local_scratchpad_preview: list[str] = Field(
        default_factory=list,
        description="Sanitized summary preview of scratchpad deductions"
    )

    model_config = ConfigDict(extra="ignore")


class MemoryItem(BaseModel):
    """Entry stored in the vector memory layer."""
    key: str
    content: str
    embedding_dim: int = Field(default=64)
    domain: DomainScope
    tags: list[str] = Field(default_factory=list)
    embedding: Optional[list[float]] = Field(default=None)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="ignore")
