"""Triage Supervisor for ATLAS Prototype 1.

Evaluates incoming task requests, searches vector memory for guidance and past solutions,
determines domain routing (MAINTENANCE vs RESEARCH_DEV), dispatches tasks to workers,
and merges final outputs into GlobalState while preserving strict LocalState isolation.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from backend.memory import VectorMemoryStore
from backend.schemas import (
    DomainScope,
    ExecutionStatus,
    GlobalState,
    LocalState,
    TaskPriority,
    TaskRequest,
    TaskResult,
    TaskType,
)
from backend.telemetry import TelemetryTracker, estimate_tokens
from backend.workers import MaintenanceWorker, RDWorker


class TriageSupervisor:
    """Central supervisor managing task classification, domain routing, and worker dispatch."""

    def __init__(self, memory_store: VectorMemoryStore, telemetry_tracker: TelemetryTracker):
        self.memory_store = memory_store
        self.tracker = telemetry_tracker
        self.global_state = GlobalState()
        self.maintenance_worker = MaintenanceWorker(telemetry_tracker)
        self.rd_worker = RDWorker(telemetry_tracker)
        # Private registry isolating worker internal LocalStates from GlobalState
        self._worker_local_states: dict[str, LocalState] = {}
        self._task_results: dict[str, TaskResult] = {}

    def get_local_state(self, task_id: str) -> Optional[LocalState]:
        """Retrieve the isolated LocalState for a specific task."""
        return self._worker_local_states.get(task_id)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve the completed TaskResult for a specific task."""
        return self._task_results.get(task_id)

    def list_task_results(self) -> list[TaskResult]:
        """List all completed task results."""
        return list(self._task_results.values())

    def _determine_domain(self, task: TaskRequest) -> tuple[DomainScope, float, str]:
        """Classify task into target domain with confidence score and rationale."""
        if task.task_type in (TaskType.BUG_FIX, TaskType.REFACTORING, TaskType.DEPENDENCY_SECURITY):
            return (
                DomainScope.MAINTENANCE,
                0.98,
                f"Task type '{task.task_type.value}' maps directly to repository maintenance, testing, and patch synthesis."
            )
        elif task.task_type == TaskType.EXPLORATION_RESEARCH:
            return (
                DomainScope.RESEARCH_DEV,
                0.96,
                "Task type 'EXPLORATION_RESEARCH' requires external literature review, benchmarking, and hypothesis testing."
            )
        elif task.task_type == TaskType.FEATURE_IMPLEMENTATION:
            # Semantic heuristic for feature requests
            text_lower = (task.title + " " + task.description).lower()
            if any(term in text_lower for term in ["architect", "spike", "evaluate", "feasibility", "compare", "research"]):
                return (
                    DomainScope.RESEARCH_DEV,
                    0.88,
                    "Feature implementation involves architectural exploration and feasibility analysis; routed to R&D."
                )
            return (
                DomainScope.MAINTENANCE,
                0.92,
                "Feature implementation involves concrete repository code additions and test suites; routed to Maintenance."
            )
        return (DomainScope.MAINTENANCE, 0.75, "Default fallback to maintenance worker.")

    def run_task(self, task: TaskRequest) -> TaskResult:
        """Execute the complete triage, retrieval, dispatch, and consolidation pipeline."""
        # 1. Update Global State: Task Ingested
        self.global_state.active_tasks[task.task_id] = task
        self.global_state.current_task_id = task.task_id

        # 2. Triage Span: Classification & Routing Decision
        with self.tracker.span(task.task_id, "triage") as triage_span:
            target_domain, confidence, rationale = self._determine_domain(task)

            # Record routing decision in GlobalState
            routing_entry = {
                "task_id": task.task_id,
                "target_domain": target_domain.value,
                "confidence": confidence,
                "rationale": rationale,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.global_state.routing_history.append(routing_entry)

            triage_span.add_tokens_in(estimate_tokens(f"{task.title} {task.description} {task.task_type.value}"))
            triage_span.add_tokens_out(estimate_tokens(f"{target_domain.value} {rationale}"))
            triage_span.set_metadata("routing_decision", routing_entry)

        # 3. Memory Retrieval Span: Query matching historical solutions & prompts
        with self.tracker.span(task.task_id, "memory_retrieval") as mem_span:
            query_text = f"{task.title} {task.description}"
            matching_memories = self.memory_store.search_memory(
                query=query_text,
                domain=target_domain,
                top_k=2,
            )

            # Select injected dynamic prompt
            prompt_key = (
                "prompt:maintenance_worker"
                if target_domain == DomainScope.MAINTENANCE
                else "prompt:rd_worker"
            )
            prompt_item = self.memory_store.get_memory(prompt_key)
            system_prompt = (
                prompt_item.content
                if prompt_item
                else "You are an autonomous ATLAS worker agent."
            )

            mem_span.add_tokens_in(estimate_tokens(query_text))
            mem_span.add_tokens_out(estimate_tokens(system_prompt + " ".join(m.content for m, _ in matching_memories)))
            mem_span.set_metadata("matches_found", len(matching_memories))
            mem_span.set_metadata("system_prompt_injected", prompt_key)

        # 4. Dispatch to Specialized Worker
        past_memory_payloads = [
            {"key": item.key, "content": item.content, "score": score}
            for item, score in matching_memories
        ]

        if target_domain == DomainScope.MAINTENANCE:
            worker_output = self.maintenance_worker.execute(task, system_prompt, past_memory_payloads)
        else:
            worker_output = self.rd_worker.execute(task, system_prompt, past_memory_payloads)

        # 5. Isolate LocalState: store in private registry, DO NOT pollute GlobalState
        isolated_local_state: LocalState = worker_output["local_state"]
        self._worker_local_states[task.task_id] = isolated_local_state

        # 6. Collect Spans for TaskResult
        task_telemetry = self.tracker.get_traces(task_id=task.task_id)

        # 7. Construct Public TaskResult
        task_result = TaskResult(
            task_id=task.task_id,
            status=ExecutionStatus.COMPLETED,
            assigned_worker=worker_output["assigned_worker"],
            result_summary=worker_output["result_summary"],
            code_patch=worker_output.get("code_patch"),
            telemetry_records=task_telemetry,
            local_scratchpad_preview=worker_output.get("local_scratchpad_preview", []),
        )

        # 8. Merge Clean Output into GlobalState
        self.global_state.completed_tasks[task.task_id] = {
            "task_id": task.task_id,
            "title": task.title,
            "status": ExecutionStatus.COMPLETED.value,
            "assigned_worker": worker_output["assigned_worker"],
            "summary": worker_output["result_summary"],
            "code_patch": worker_output.get("code_patch"),
        }
        self.global_state.final_output = {
            "task_id": task.task_id,
            "status": ExecutionStatus.COMPLETED.value,
            "worker": worker_output["assigned_worker"],
            "summary": worker_output["result_summary"],
        }
        self.global_state.current_task_id = None
        if task.task_id in self.global_state.active_tasks:
            del self.global_state.active_tasks[task.task_id]

        self._task_results[task.task_id] = task_result
        return task_result
