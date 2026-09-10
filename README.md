# ATLAS
A Triaged Learning Agent Syndicate

## Project Objective
* **Goal:** A self-improving, multi-agent backend for task triage, R&D, and code maintenance.
* **Mechanism:** Autonomous routing, execution via sandboxed tools, and offline optimization of system prompts/tools to reduce latency and token spend.

## Technology Stack
| Subsystem | Framework/Tech | Primary Function |
| :--- | :--- | :--- |
| **Orchestration** | LangGraph (Python) | Graph-based state machine, multi-agent routing |
| **State Validation**| Pydantic | Enforcing strict Global vs. Local memory schemas |
| **Tool Boundaries** | Model Context Protocol (MCP)| Standardized, domain-isolated tool endpoints |
| **Memory** | PostgreSQL + `pgvector` | Long-term vector/relational storage |
| **Observability** | Pydantic Logfire | OpenTelemetry tracking of Pydantic state/tokens |

## Subsystem Breakdown

### 1. Orchestration & State (LangGraph + Pydantic)
* **Triage Agent (Supervisor):** Routes incoming requests to domain-specific Worker Agents.
* **Worker Agents (R&D, Maintenance):** Execute tasks within specific domains.
* **Global State:** Pydantic model tracking the task queue and final outputs (shared across system).
* **Local State:** Isolated scratchpads for intermediate reasoning, tool retries, and errors (hidden from Supervisor to prevent context pollution).

### 2. Tool Boundaries (MCP)
* **Standardization:** Tools are exposed as uniform endpoints rather than raw code execution blocks.
* **Context Isolation:** Strict access control. (e.g., Maintenance Agent only accesses Git/Filesystem endpoints; R&D Agent only accesses search/scraping endpoints).

### 3. Long-Term Memory (pgvector)
* **Storage:** Houses dynamic system prompts, tool definitions, and successful historical task solutions.
* **Retrieval:** Enables agents to perform semantic similarity searches (e.g., finding past solutions to similar bugs) without overloading the LLM context window.

### 4. Observability & Telemetry (Pydantic Logfire)
* **Integration:** Wraps the LangGraph environment as a transparent telemetry layer.
* **State Tracking:** Synchronously intercepts, serializes, and logs Pydantic state changes at every graph node.
* **Metrics:** Correlates token consumption and execution latency directly to specific tools or agents.
* **Error Catching:** Surfaces silent failures where an agent hallucinates a fix after an unhandled tool error.

## The Self-Improvement Loop (Data Flow)
1. **Live Execution:** Live agents process tasks, dynamically pulling context and tools from `pgvector`.
2. **Telemetry Capture:** `Logfire` transparently records every token, API call, and state transition.
3. **Asynchronous Analysis:** An offline Meta-Improver Agent queries `Logfire` traces to identify bottlenecks, token waste, or tool retry loops.
4. **Optimization:** The Meta-Improver generates an optimized system prompt or more efficient tool query.
5. **Database Update:** The new optimization is embedded and pushed to `pgvector`, ready for the live agents to consume on the next matching task.
