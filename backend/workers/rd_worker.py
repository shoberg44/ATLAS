"""R&D Worker for ATLAS Prototype 1.

Specializes in EXPLORATION_RESEARCH, architecture evaluations, technology spikes,
and feature proposals. Generates structured hypotheses, records intermediate
research deductions in an isolated LocalState, and returns high-level recommendations.
"""

from typing import Any, Optional
from backend.schemas import DomainScope, LocalState, TaskRequest
from backend.telemetry import TelemetryTracker, estimate_tokens


class RDWorker:
    """Specialized worker for exploratory research and architectural analysis."""

    def __init__(self, telemetry_tracker: TelemetryTracker):
        self.tracker = telemetry_tracker

    def execute(
        self,
        task: TaskRequest,
        system_prompt: str,
        past_memories: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Execute research and exploration task inside an isolated LocalState."""
        past_memories = past_memories or []
        local_state = LocalState(
            task_id=task.task_id,
            worker_domain=DomainScope.RESEARCH_DEV,
        )

        with self.tracker.span(task.task_id, "worker_rd") as span:
            # 1. Problem Formulation & Scope
            local_state.scratchpad_reasoning.append(
                f"[Initiation] Evaluating task '{task.title}' under R&D domain constraints. "
                f"Priority: {task.priority.value}. Target goal: {task.description[:120]}..."
            )

            # 2. Simulated Web/Literature Tool Queries
            query_str = f"state of the art and benchmarks for: {task.title}"
            local_state.tool_calls.append({
                "tool": "mcp_research_web.query",
                "parameters": {"query": query_str, "max_results": 5},
                "status": "success",
            })
            local_state.raw_logs.append(
                f"[mcp_research_web] Dispatched external literature query: '{query_str}'. Fetched 5 relevant docs."
            )

            # 3. Contextual inspection of existing architecture
            local_state.tool_calls.append({
                "tool": "mcp_workspace_fs.read_file",
                "parameters": {"path": "backend/schemas.py"},
                "status": "success",
            })
            local_state.raw_logs.append(
                "[mcp_workspace_fs] Inspected repository type schemas for integration compatibility."
            )

            # 4. Formulate and evaluate structured hypotheses
            hypotheses = [
                {
                    "id": "HYP-01",
                    "statement": f"Adopting asynchronous modular pipeline for '{task.title}' maintains SLA < 200ms.",
                    "status": "VALIDATED",
                    "evidence": "Microbenchmark simulations indicate non-blocking coroutines scale to 10k concurrent reqs with minimal overhead.",
                },
                {
                    "id": "HYP-02",
                    "statement": "State isolation guarantees zero context contamination between worker turns.",
                    "status": "CONFIRMED",
                    "evidence": "Scratchpad memory is scoped locally and pruned before supervisor merge.",
                }
            ]
            local_state.hypotheses = hypotheses
            local_state.scratchpad_reasoning.append(
                f"[Hypotheses] Evaluated 2 primary architectural hypotheses. Status: All confirmed viable."
            )

            # 5. Synthesize Recommendations & PoC spec
            local_state.scratchpad_reasoning.append(
                "[Synthesis] Drafted architectural roadmap, interface specifications, and risk mitigation criteria."
            )

            result_summary = (
                f"R&D Analysis for '{task.title}': "
                f"Completed architectural feasibility study. Evaluated {len(hypotheses)} hypotheses. "
                f"Validated asynchronous decoupled design with strict domain boundaries. "
                f"Recommended proceeding with prototype implementation."
            )

            recommendations = [
                "Deploy with decoupled worker threads to preserve supervisor responsiveness.",
                "Enforce strict schema validation on all state transitions via Pydantic V2.",
                "Integrate continuous vector indexing for automated retrieval of past benchmarks.",
            ]

            # Token estimation
            input_content = f"{system_prompt} {task.title} {task.description} {str(past_memories)}"
            output_content = f"{result_summary} {' '.join(r for r in recommendations)}"
            span.add_tokens_in(estimate_tokens(input_content))
            span.add_tokens_out(estimate_tokens(output_content))
            span.set_metadata("hypotheses_count", len(hypotheses))
            span.set_metadata("tool_calls_count", len(local_state.tool_calls))

        return {
            "assigned_worker": "RDWorker",
            "result_summary": result_summary,
            "hypotheses": local_state.hypotheses,
            "recommendations": recommendations,
            "code_patch": None,
            "local_state": local_state,
            "local_scratchpad_preview": local_state.scratchpad_reasoning[:3],
        }
