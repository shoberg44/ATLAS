# ATLAS Prototype 1: Architectural Decisions & System Specification
**A Triaged Learning Agent Syndicate**

---

## 1. Executive Summary & Purpose

ATLAS (A Triaged Learning Agent Syndicate) is an autonomous, self-improving multi-agent backend engineered for intelligent task triage, research and development (R&D), and automated code maintenance. The core premise of ATLAS is that high-reliability autonomous software engineering cannot rely on a single monolithic agent with an unbounded context window. Instead, ATLAS divides responsibilities across specialized, domain-isolated agents orchestrated by a centralized supervisor, bounded by strict tool capabilities (via Model Context Protocol), verified against rigorous state schemas (via Pydantic V2), and optimized over time through an offline, telemetry-driven meta-improvement feedback loop.

This document establishes the authoritative architectural blueprint, interface contracts, data models, and infrastructure decisions for **Prototype 1**.

---

## 2. System Inputs Specification

Every operation in ATLAS begins with a structured ingestion format. Raw user inputs or upstream webhook events are normalized into strictly typed Pydantic structures.

```
                          ┌────────────────────────┐
                          │   Raw User / Webhook   │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │ Ingestion & Normalizer │
                          └───────────┬────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │     AtlasTaskRequest      │
                        │ ───────────────────────── │
                        │ • task_id                 │
                        │ • task_type               │
                        │ • domain_scope            │
                        │ • priority                │
                        │ • constraints             │
                        │ • code_context            │
                        │ • user_goals              │
                        └───────────────────────────┘
```

### 2.1 Task Definitions
- **`task_id`**: Globally unique identifier (UUIDv4) tracking the lifecycle of the task across the state graph, database records, and OpenTelemetry/Logfire spans.
- **`submitted_at`**: ISO-8601 UTC timestamp of task creation.
- **`created_by`**: Source identifier (e.g., `user:<id>`, `github_webhook:<repo>`, `cron:<id>`).
- **`title`**: Concise human-readable task summary.
- **`description`**: Detailed task narrative describing the desired outcome or defect.

### 2.2 Task Types
Tasks are partitioned into deterministic operational categories:
1. **`BUG_FIX`**: Corrective maintenance addressing regressions, failing test cases, or exceptions.
2. **`FEATURE_IMPLEMENTATION`**: Additive changes introducing new functionality against existing interfaces.
3. **`EXPLORATION_RESEARCH`**: Open-ended R&D, feasibility studies, technology spikes, or architectural evaluations.
4. **`REFACTORING`**: Codebase restructuring without functional alteration (clean code, pattern migration, performance tuning).
5. **`DEPENDENCY_SECURITY`**: Dependency upgrades, vulnerability patching, or configuration remediation.

### 2.3 Domain Scopes
Domain boundaries prevent accidental cross-contamination of execution environments:
- **`MAINTENANCE`**: Scoped strictly to repository internal files, test suites, build pipelines, and git history. Destructive network requests are forbidden.
- **`RESEARCH_DEV`**: Scoped to web search, API documentation fetching, external reference extraction, and prototype sandbox scripts. Direct repository commit writes are forbidden until reviewed.
- **`TRIAGE`**: Pure evaluation domain. Has zero execution tool permissions; restricted solely to classification and routing.

### 2.4 Constraints
Constraints define hard guardrails for agent autonomy:
- **`timeout_seconds`**: Maximum wall-clock execution time allowed before emergency termination (default: 300s).
- **`max_token_budget`**: Hard token cap per task across all agent turns (default: 100,000 tokens).
- **`cost_budget_usd`**: Maximum permissible LLM API spend in dollars.
- **`allowed_paths`**: Whitelist of relative directory and file paths the agent may inspect or edit.
- **`prohibited_paths`**: Blacklist of sensitive paths (e.g., `.env`, `.git/`, `credentials/`).
- **`require_human_approval`**: Boolean requiring explicit human-in-the-loop (HITL) sign-off prior to patch application.

### 2.5 Code Snippets & Context
- **`target_files`**: List of target relative file paths relevant to the request.
- **`code_snippets`**: Key code blocks, snippets, or AST references provided by the user.
- **`stack_traces`**: Raw error logs, runtime exceptions, or failing test traces.
- **`reproduction_steps`**: Structured steps or test commands (e.g., `pytest tests/test_core.py -k test_edge_case`).

### 2.6 User Goals & Acceptance Criteria
- **`primary_goal`**: Concrete statement of success (e.g., "Make `test_token_refresh` pass").
- **`acceptance_criteria`**: Explicit checklist of conditions required for task completion.
- **`benchmark_evals`**: Specific test suites or linters that must pass with return code 0.

### 2.7 Priority Levels
- **`P0 (Critical / Blocker)`**: Immediate preemption, routing to most capable models (e.g., Claude 3.5 Sonnet / GPT-4o), parallelized worker allocation, SLA < 5 min.
- **`P1 (High)`**: Priority execution queue, standard worker models, SLA < 30 min.
- **`P2 (Medium)`**: Standard batch queue, standard worker models with token optimization.
- **`P3 (Low / Backlog)`**: Background execution, cost-optimized smaller models (e.g., Claude 3.5 Haiku / GPT-4o-mini).

---

## 3. System Outputs Specification

System outputs represent the immutable audit trail and functional artifacts resulting from agent execution.

```
                          ┌───────────────────────────┐
                          │     AtlasTaskResponse     │
                          └─────────────┬─────────────┘
                                        │
      ┌──────────────────┬──────────────┴─────┬──────────────────┐
      ▼                  ▼                    ▼                  ▼
┌─────────────┐   ┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│   Triage    │   │  Code Patch   │   │  Execution   │   │  Telemetry   │
│  Decision   │   │  & Artifacts  │   │    Status    │   │  & Metrics   │
└─────────────┘   └───────────────┘   └──────────────┘   └──────────────┘
```

### 3.1 Triage Decisions
- **`assigned_worker`**: Designated target agent (`worker_maintenance`, `worker_research`, or `escalation_human`).
- **`classification_confidence`**: Float value (`0.0` to `1.0`) indicating model certainty.
- **`triage_rationale`**: Structured explanation of routing heuristics and domain matching.
- **`dynamic_prompt_injected`**: ID or version of the specialized prompt loaded from vector memory.

### 3.2 Domain Assignments
- **`sandbox_id`**: Active container or scoped filesystem session ID.
- **`mcp_toolsets_granted`**: Exact whitelist of MCP tool namespaces provided to the worker.

### 3.3 Worker Reasoning Artifacts
- **`scratchpad_summary`**: High-level synthesis of worker deduction (scrubbed of noisy raw tool outputs).
- **`hypotheses_tested`**: List of proposed root causes and validation outcomes.
- **`validation_output`**: Raw output from verification commands (test results, linter outputs).

### 3.4 Code Modifications / Patches
- **`patch_format`**: Standard Unified Diff format (git-compatible diffs).
- **`modified_files`**: Explicit list of files created, modified, or deleted.
- **`syntax_validation`**: Boolean indicating that AST parsing succeeded without syntax errors.
- **`rollback_patch`**: Inverted patch allowing instant zero-downtime rollback.

### 3.5 Execution Status
Lifecycle states tracked in the global state machine:
- `PENDING`: Task queued, awaiting ingestion.
- `TRIAGED`: Task classified and routed to worker.
- `RUNNING`: Worker actively executing and calling tools.
- `AWAITING_APPROVAL`: Execution paused; human approval required via LangGraph interrupt.
- `COMPLETED`: Work verified against acceptance criteria and finished.
- `FAILED`: Execution terminated due to errors, budget exhaustion, or timeout.
- `ROLLED_BACK`: Patch was reverted following validation failure.

### 3.6 Token & Latency Metrics
- **`total_latency_ms`**: Total round-trip duration from submission to completion.
- **`node_latencies`**: Dictionary mapping each graph node to its execution duration in milliseconds.
- **`token_usage`**:
  * `input_tokens`: Total prompt tokens consumed.
  * `output_tokens`: Total completion tokens generated.
  * `cached_tokens`: Tokens read from prompt caching mechanisms.
- **`cost_usd`**: Estimated total financial cost of the task execution.

### 3.7 Self-Improvement Suggestions
- **`telemetry_trace_id`**: Logfire trace ID referencing the complete execution graph.
- **`optimization_candidate`**: Identification of redundant tool loops, excessive prompts, or high-latency steps.
- **`suggested_prompt_delta`**: Proposed improvement to system prompts stored in vector memory.

---

## 4. System Requirements

### 4.1 Pydantic Validation
- Strict Pydantic V2 models (`pydantic.BaseModel`) are mandatory across all public boundaries: HTTP request/response, LangGraph state structures, tool parameters, and database serialization.
- `model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)` applied to prevent malformed or untracked state mutations.

### 4.2 Python 3.11+
- Leverages modern language features:
  * Strict type hint syntax (`X | Y` union types, `Self`, `TypeVar`).
  * `asyncio.TaskGroup` for safe concurrent tool execution.
  * Exception groups (`ExceptionGroup`) for aggregated failure propagation.
  * Native C-optimized performance improvements in Python 3.11/3.12 runtimes.

### 4.3 Locally Scoped Execution
- Agent file modifications and command execution are restricted strictly to designated subdirectories (e.g., `demos/prototype-1/` or repository root targets).
- Path traversal outside workspace boundaries (`../..`) is detected and rejected at the validation layer.

### 4.4 Strict Global State vs. Local State Isolation
One of the most critical architectural requirements in ATLAS is preventing **context pollution**:
- **Global State**: Minimalist, high-level task state. Contains only the task definition, high-level status, final patch, and public results. This state is visible to the Supervisor (Triage Agent).
- **Local State**: Agent-specific execution scratchpad. Houses intermediate thoughts, raw tool payloads, shell output, HTTP responses, and retry loops. Local state is discarded or condensed upon completion of the worker's turn. The Supervisor never sees the worker's internal scratchpad.

```
┌────────────────────────────────────────────────────────────────────────┐
│                              GLOBAL STATE                              │
│  task_id | task_type | status | final_patch | public_metrics           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (delegates)
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │                LOCAL STATE (Worker Scratchpad)            │
       │  intermediate_reasoning | tool_call_history | raw_errors │
       │  hypotheses | partial_diffs | debug_logs                 │
       │                                                          │
       │  [ISOLATED FROM SUPERVISOR CONTEXT WINDOW]               │
       └──────────────────────────────────────────────────────────┘
```

### 4.5 Asynchronous Execution
- All network and I/O operations are non-blocking: FastAPI endpoint routes (`async def`), LangGraph nodes (`async def node_fn()`), and MCP client communication.
- Prevents thread starvation during long-running LLM streaming responses or tool executions.

### 4.6 Tool Boundary Enforcement via MCP
- Agents do not directly execute arbitrary shell scripts or import unchecked Python libraries.
- All capabilities are declared as Model Context Protocol (MCP) tools with explicit JSON Schema specifications and sandboxed handlers.
- Capability isolation: Triage has **zero** tools; Research has **read-only/web** tools; Maintenance has **scoped workspace edit/test** tools.

### 4.7 Mock & Real Vector Memory Compatibility
- Unified abstract repository pattern (`VectorMemoryBackend`) with two swappable implementations:
  1. `MockVectorMemory`: In-memory dictionary with cosine similarity computation via NumPy/scikit-learn or pure Python for zero-dependency local testing and rapid unit testing.
  2. `PgVectorMemory`: Enterprise-grade PostgreSQL + `pgvector` backend with HNSW indexing, halfvec support, and connection pooling via `asyncpg`.

### 4.8 Telemetry and Token Tracing
- Native integration with Pydantic Logfire / OpenTelemetry.
- Automatic span creation around state transitions, agent handoffs, tool calls, and LLM requests.
- Direct correlation between token usage and specific agents/nodes.

---

## 5. Infrastructure Decisions

### 5.1 Orchestration Engine: LangGraph StateGraph vs. Standalone State Machine

```
Option A: Custom Async State Machine          Option B: LangGraph StateGraph (Selected)
┌────────────────────────────────┐            ┌────────────────────────────────┐
│  while state.status != DONE:   │            │ StateGraph(GlobalState)        │
│    step = dispatch(state)      │            │   .add_node("triage", ...)     │
│    state = step.execute()      │            │   .add_node("maintenance", ...)│
│  (Custom cycles & persistence) │            │   .add_conditional_edges(...)  │
└────────────────────────────────┘            └────────────────────────────────┘
```

#### Evaluation:
- **Custom Standalone State Machine**:
  * *Pros*: Minimal dependencies, total control over runtime loop, no framework abstraction overhead.
  * *Cons*: Reinventing checkpointing, graph cycles, time-travel debugging, parallel branching, and human-in-the-loop pause/resume logic.
- **LangGraph (`StateGraph`)**:
  * *Pros*: Built-in cyclic graph primitives, first-class checkpointers (`MemorySaver`, `AsyncPostgresSaver`), native human approval support via `interrupt()`, seamless sub-graph composition for worker local states, and widespread ecosystem adoption.
  * *Cons*: Additional framework dependencies.

#### Decision:
**Adopt LangGraph `StateGraph` as the orchestration engine.**
LangGraph's native support for cyclic graphs, conditional routing, state reduction channels (`Annotated[list, add]`), and built-in human interruption provides the ideal foundation for the multi-agent syndicate. For Prototype 1, an asynchronous `StateGraph` manages the triage-to-worker pipeline, with isolated sub-graphs managing local scratchpads.

---

### 5.2 State Validation & Serialization: Pydantic V2

#### Evaluation:
- **Python `TypedDict` / Standard `dataclasses`**:
  * *Pros*: Standard library, zero dependencies.
  * *Cons*: No runtime type enforcement, weak deserialization, lacks automated JSON Schema export.
- **Pydantic V2**:
  * *Pros*: Implemented in Rust (`pydantic-core`) with up to 20x performance speedup; strict validation modes; seamless serialization to/from JSON; deep native integration with FastAPI and Logfire; automatic OpenAPI/JSON-Schema generation.

#### Decision:
**Standardize on Pydantic V2 for all data structures.**
Every domain object, state container, input payload, and output artifact must inherit from `pydantic.BaseModel`. Models must implement strict type constraints and custom validators for syntax checks, path sanitization, and metric aggregations.

---

### 5.3 Tool Boundaries: Model Context Protocol (MCP)

```
┌──────────────┐                  Standardized JSON-RPC 2.0
│ ATLAS Agent  │ ◄─────────────────────────────────────────────► ┌────────────────────┐
│ (MCP Client) │   tools/list, tools/call (filesystem, git)      │  MCP Tool Server   │
└──────────────┘                                                 └────────────────────┘
```

#### Evaluation:
- **Direct Function Calling (In-Process Python Functions)**:
  * *Pros*: Simplest to write initially; minimal IPC overhead.
  * *Cons*: No process sandboxing; potential security risks; agents can compromise runtime memory; difficult to isolate permissions across workers.
- **Model Context Protocol (MCP)**:
  * *Pros*: Open standard developed by Anthropic; client/server architecture isolating tools into dedicated processes; standard JSON-RPC 2.0 communication over `stdio` or `HTTP/SSE`; strict capability negotiation and granular tool exposure.

#### Decision:
**Standardize on Model Context Protocol (MCP) for tool boundary enforcement.**
- Communication channel: `stdio` for local Prototype 1 execution (subprocesses launched per toolset).
- Future readiness: Architecture allows swapping `stdio` transports for remote HTTP/SSE endpoints without modifying agent code.
- Toolsets:
  * `mcp-workspace-fs`: Sandboxed file read/write within allowed directories.
  * `mcp-git`: Scoped git operations (status, diff, branch, commit).
  * `mcp-research-web`: Search and documentation scraping for R&D agents.

---

### 5.4 Long-Term Memory: PostgreSQL + pgvector vs. Mock

```
                               ┌─────────────────────────────────┐
                               │     VectorMemoryBackend (ABC)   │
                               └────────────────┬────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     ▼                                                     ▼
    ┌─────────────────────────────────┐                   ┌─────────────────────────────────┐
    │        MockVectorMemory         │                   │        PgVectorMemory           │
    │  (In-Memory + Cosine Sim)       │                   │  (PostgreSQL 16 + pgvector)     │
    │  • Zero dependencies            │                   │  • HNSW Indexing                │
    │  • Rapid local development      │                   │  • Halfvec Quantization         │
    │  • Synchronous / Async test     │                   │  • Relational + Vector Joins    │
    └─────────────────────────────────┘                   └─────────────────────────────────┘
```

#### Evaluation:
- **Dedicated Vector DBs (Chroma, Pinecone, Qdrant)**:
  * Decoupled vector stores force a dual-database architecture: relational data in Postgres, vectors in another system. This requires distributed transactions and dual backups.
- **PostgreSQL + `pgvector`**:
  * Unified operational simplicity: stores relational task records, users, audit logs, AND vector embeddings in the same database engine with ACID transactions.
  * Supports HNSW (Hierarchical Navigable Small World) indexing for millisecond-scale nearest neighbor search, `halfvec` for 50% memory reduction, and hybrid search (filtering relational metadata while ranking vector similarities).

#### Decision:
**Implement a dual-mode Vector Memory Architecture with an Abstract Base Class (`VectorMemoryBackend`):**
1. **Prototype 1 Baseline**: `MockVectorMemory` operating in-memory using cosine similarity for lightning-fast bootstrapping, zero external docker requirements during initial prototyping, and deterministic test execution.
2. **Production Path**: `PgVectorMemory` utilizing PostgreSQL 16+ and `pgvector` extension. The schema definition includes:
   * Table `task_solutions`: historical tasks, embeddings of task descriptions, patch results.
   * Table `dynamic_prompts`: agent system prompts, performance scores, versioning, embeddings for task-similarity retrieval.
   * Table `tool_embeddings`: semantically indexed tool definitions for dynamic tool retrieval.

---

### 5.5 Observability & Telemetry: Pydantic Logfire

#### Evaluation:
- **Standard Logging (`logging`, `loguru`)**:
  * Lacks span hierarchy, distributed trace correlation, token metrics, or structural inspection of deep objects.
- **Pydantic Logfire**:
  * Purpose-built for Python and Pydantic.
  * Deep native integration: automatically serializes and parses Pydantic models inside trace spans.
  * OpenTelemetry-native: exports standard OTel spans while providing a rich web dashboard.
  * Token attribution: captures exact input/output tokens per node, enabling precise cost attribution to individual agents and prompt variations.
  * Unhandled error detection: surfaces cases where an LLM silently hallucinates after a hidden tool failure.

#### Decision:
**Embed Pydantic Logfire as the standard telemetry layer.**
Every node in the LangGraph graph executes inside a configured Logfire span. State changes are automatically captured as Pydantic models. Traces provide the foundational data queried by the offline meta-improver loop.

---

### 5.6 Frontend & Visualization

#### Evaluation:
- **Streamlit / Gradio**:
  * Quick to build, but tightly coupled to Python execution loops; difficult to embed cleanly into modern microservice frontends or provide low-latency streaming state updates.
- **FastAPI REST + Server-Sent Events (SSE) / WebSockets + Lightweight Dashboard**:
  * Decoupled, production-ready architecture.
  * Exposes clean REST API for task submission, cancellation, and retrieval.
  * Streams real-time graph state transitions to client interfaces via SSE.
  * Enables a clean web dashboard (HTML5/Tailwind/React) to render real-time agent execution graphs, node states, and token counters.

#### Decision:
**Implement a FastAPI backend with SSE streaming endpoints and a clean local inspection dashboard.**
- API endpoints:
  * `POST /api/v1/tasks`: Submit new task.
  * `GET /api/v1/tasks/{task_id}`: Retrieve task status and artifacts.
  * `GET /api/v1/tasks/{task_id}/events`: Server-Sent Events (SSE) stream of real-time state deltas.
  * `POST /api/v1/tasks/{task_id}/approve`: Resume interrupted task (HITL).
- Web UI: Minimalist, responsive dashboard rendering the live LangGraph execution sequence, active agent thoughts, and generated diffs.

---

### 5.7 Self-Improvement Architecture: Offline Meta-Improver Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ONLINE LIVE EXECUTION                           │
│  Task Ingestion ──► Triage ──► Worker Execution ──► Verification ──► Done   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Logfire Telemetry (Spans, Tokens, Diffs)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OFFLINE META-IMPROVER LOOP                           │
│                                                                             │
│  1. Ingest Logfire Traces & Error Clusters                                  │
│  2. Identify High-Token or Failing Patterns                                 │
│  3. Formulate Mutated Prompts / Tool Schemas                                │
│  4. Evaluate Mutation on Golden Benchmark Dataset                           │
│  5. If Performance Delta > Baseline ──► Commit New Version to pgvector      │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Evaluation:
- **Online Self-Reflection (Reflection in the same execution loop)**:
  * High risk of compounding errors, context explosion, and excessive latency for the user.
- **Offline Asynchronous Meta-Improver**:
  * Completely decouples performance optimization from live task latency.
  * Analyzes aggregated logs over dozens or hundreds of tasks.
  * Uses clustering algorithms to isolate common failure points (e.g., "Worker Maintenance frequently gets stuck in 3-turn loops editing `conftest.py`").
  * Generates candidate prompt updates and evaluates them against an automated benchmark test suite before updating the production vector memory.

#### Decision:
**Implement the Offline Asynchronous Meta-Improver pattern.**
Live execution focuses purely on fast, deterministic task completion. The meta-improver runs asynchronously as an offline batch process, mining Logfire traces and updating the prompt/solution knowledge base in PostgreSQL/pgvector.

---

## 6. Implementation Phasing Matrix

| Component | Prototype 1 (Scope) | Production Target |
| :--- | :--- | :--- |
| **API Server** | FastAPI (local server on port 8000) | Distributed containerized FastAPI cluster |
| **Orchestration** | LangGraph StateGraph (in-memory state) | LangGraph + AsyncPostgresSaver checkpointer |
| **State Models** | Pydantic V2 GlobalState & LocalState | Versioned Pydantic V2 schemas with database ORM mappings |
| **Agents** | Triage Agent + Maintenance Worker + R&D Worker | Full Syndicate (Triage, Maintenance, R&D, Reviewer, Security) |
| **Tool Interface** | Sandboxed local file & shell tools via MCP structure | Dedicated multi-container MCP servers |
| **Vector Memory** | `MockVectorMemory` (in-memory cosine similarity) | PostgreSQL 16 + `pgvector` with HNSW & halfvec |
| **Telemetry** | Pydantic Logfire instrumentation hooks & local logging | Cloud Pydantic Logfire / OTel collector pipeline |
| **Web UI** | Static inspection dashboard via FastAPI static files | Next.js / React full operational console |
| **Self-Improvement**| Metric extraction and synthetic prompt evaluation hook | Autonomous offline batch meta-improver daemon |

---

## 7. Next Steps for Prototype 1 Execution

1. **Environment Setup & Verification**: Establish the isolated `.venv` with `fastapi`, `uvicorn`, `pydantic`, `python-multipart`.
2. **Schema Implementation**: Build `models/schemas.py` declaring `AtlasTaskRequest`, `GlobalState`, `LocalWorkerState`, and `AtlasTaskResponse`.
3. **Memory Layer**: Implement `memory/vector_store.py` with `VectorMemoryBackend` and `MockVectorMemory`.
4. **Agent Graph**: Construct `orchestrator/graph.py` assembling the LangGraph StateGraph with Triage and Worker nodes.
5. **API & Server**: Implement `main.py` exposing FastAPI endpoints and live task runner.
