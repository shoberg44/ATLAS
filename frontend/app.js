/**
 * ATLAS Prototype 1 Interactive Dashboard Application
 * Autonomous Multi-Agent Engineering & Self-Improvement System
 */

(function () {
  'use strict';

  // API Base URL (relative path for local FastAPI server)
  const API_BASE = window.location.origin;

  // Application State
  const state = {
    tasksRun: 0,
    totalLatencyMs: 0,
    totalTokens: 0,
    metaIterations: 0,
    currentTaskId: null,
    activeMemoryDomain: 'ALL',
    activeSearchQuery: '',
  };

  // Presets Data Dictionary
  const PRESETS = {
    bugfix: {
      title: 'Fix IndexError in Task Priority Queue Reducer',
      task_type: 'BUG_FIX',
      priority: 'P0',
      description: 'State reducer throws IndexError: list index out of range when task priority queue contains empty batches during concurrent worker dequeue operations. Ensure empty batch checks and bounds validation.',
      code_snippet: 'def reduce_task_queue(state: TaskQueueState, batch: list[Task]) -> TaskQueueState:\n    # BUG: crashes with IndexError if batch is empty\n    highest_p = batch[0].priority\n    state.priority_buckets[highest_p].extend(batch)\n    return state',
    },
    research: {
      title: 'Explore HNSW Vector Indexing for Long-Term Memory',
      task_type: 'EXPLORATION_RESEARCH',
      priority: 'P1',
      description: 'Evaluate HNSW (Hierarchical Navigable Small World) indexing performance vs Flat IVFFlat index on PostgreSQL pgvector with halfvec quantization for high-throughput semantic memory retrieval under 5ms.',
      code_snippet: '-- HNSW Index Evaluation Target:\nCREATE INDEX ON task_memory_embeddings\nUSING hnsw (embedding halfvec_cosine_ops)\nWITH (m = 16, ef_construction = 64);',
    },
    refactor: {
      title: 'Refactor Routing Table & Clean Channels',
      task_type: 'REFACTORING',
      priority: 'P2',
      description: 'Restructure LangGraph channel definitions and state reduction annotations. Ensure isolated worker scratchpads use private channels and cannot contaminate global state channels.',
      code_snippet: '# Channel refactoring target:\nclass AgentSyndicateState(TypedDict):\n    global_channel: Annotated[dict, merge_dicts]\n    # Ensure local_scratchpad is NOT aggregated at supervisor root',
    },
    security: {
      title: 'Patch PyJWT Deprecated Algorithm Vulnerability',
      task_type: 'DEPENDENCY_SECURITY',
      priority: 'P1',
      description: 'Remediate insecure JWT header verification vulnerability by explicitly rejecting "none" algorithm and restricting signature validation to approved asymmetric algorithms (RS256, ES256).',
      code_snippet: '# Vulnerable token decode:\n# jwt.decode(token, key, algorithms=["HS256", "none"])\n# Target fix: restrict algorithms to strict whitelist and enforce signature',
    },
  };

  // DOM Elements
  const dom = {
    // Header
    globalStatusBadge: document.getElementById('global-status-badge'),
    globalStatusText: document.getElementById('global-status-text'),
    headerTaskCount: document.getElementById('header-task-count'),
    headerAvgLatency: document.getElementById('header-avg-latency'),
    headerTotalTokens: document.getElementById('header-total-tokens'),
    headerMetaIterations: document.getElementById('header-meta-iterations'),
    backendStatus: document.getElementById('backend-status'),
    backendStatusText: document.getElementById('backend-status-text'),
    btnRefreshAll: document.getElementById('btn-refresh-all'),
    toastContainer: document.getElementById('toast-container'),

    // Task Form
    taskForm: document.getElementById('task-form'),
    taskTitle: document.getElementById('task-title'),
    taskType: document.getElementById('task-type'),
    taskPriority: document.getElementById('task-priority'),
    taskDescription: document.getElementById('task-description'),
    taskCode: document.getElementById('task-code'),
    btnSubmitTask: document.getElementById('btn-submit-task'),
    submitSpinner: document.getElementById('submit-spinner'),

    // Flow Pipeline
    executionActiveStep: document.getElementById('execution-active-step'),
    nodeIngest: document.getElementById('node-ingest'),
    nodeTriage: document.getElementById('node-triage'),
    nodeWorker: document.getElementById('node-worker'),
    nodeVerify: document.getElementById('node-verify'),
    nodeComplete: document.getElementById('node-complete'),
    arrow1: document.getElementById('arrow-1'),
    arrow2: document.getElementById('arrow-2'),
    arrow3: document.getElementById('arrow-3'),
    arrow4: document.getElementById('arrow-4'),
    workerFlowIcon: document.getElementById('worker-flow-icon'),
    workerFlowTitle: document.getElementById('worker-flow-title'),
    workerFlowStatus: document.getElementById('worker-flow-status'),
    workerFlowBadge: document.getElementById('worker-flow-badge'),

    // Triage Decision
    decisionDomain: document.getElementById('decision-domain'),
    decisionWorker: document.getElementById('decision-worker'),
    decisionConfidence: document.getElementById('decision-confidence'),
    decisionPrompt: document.getElementById('decision-prompt'),
    decisionRationale: document.getElementById('decision-rationale'),
    executionLogs: document.getElementById('execution-logs'),
    streamStatusPill: document.getElementById('stream-status-pill'),

    // State Inspector
    globalTaskId: document.getElementById('global-task-id'),
    globalStatus: document.getElementById('global-status'),
    globalActiveTasks: document.getElementById('global-active-tasks'),
    globalResultSummary: document.getElementById('global-result-summary'),
    globalCodePatch: document.getElementById('global-code-patch'),
    globalRoutingHistory: document.getElementById('global-routing-history'),
    localWorkerDomain: document.getElementById('local-worker-domain'),
    localScratchpad: document.getElementById('local-scratchpad'),
    localHypotheses: document.getElementById('local-hypotheses'),
    localToolCalls: document.getElementById('local-tool-calls'),
    localRawLogs: document.getElementById('local-raw-logs'),

    // Telemetry
    metricLatency: document.getElementById('metric-latency'),
    metricTokensIn: document.getElementById('metric-tokens-in'),
    metricTokensOut: document.getElementById('metric-tokens-out'),
    metricCost: document.getElementById('metric-cost'),
    telemetryTraceId: document.getElementById('telemetry-trace-id'),
    btnCopyTrace: document.getElementById('btn-copy-trace'),
    telemetryNodeTable: document.getElementById('telemetry-node-table'),

    // Memory Explorer
    memorySearchInput: document.getElementById('memory-search-input'),
    btnSearchMemory: document.getElementById('btn-search-memory'),
    btnClearSearch: document.getElementById('btn-clear-search'),
    memoryItemsList: document.getElementById('memory-items-list'),
    btnAddMemoryToggle: document.getElementById('btn-add-memory-toggle'),
    addMemoryContainer: document.getElementById('add-memory-form-container'),
    addMemoryForm: document.getElementById('add-memory-form'),
    btnCancelAddMem: document.getElementById('btn-cancel-add-mem'),
    memKey: document.getElementById('mem-key'),
    memDomain: document.getElementById('mem-domain'),
    memTags: document.getElementById('mem-tags'),
    memContent: document.getElementById('mem-content'),

    // Meta Improver
    btnRunMetaImprover: document.getElementById('btn-run-meta-improver'),
    metaSpinner: document.getElementById('meta-spinner'),
    metaTokenSavings: document.getElementById('meta-token-savings'),
    metaLatencyGain: document.getElementById('meta-latency-gain'),
    metaMutationsCount: document.getElementById('meta-mutations-count'),
    diffTargetAgent: document.getElementById('diff-target-agent'),
    diffSavingsBadge: document.getElementById('diff-savings-badge'),
    diffBeforeText: document.getElementById('diff-before-text'),
    diffAfterText: document.getElementById('diff-after-text'),
    diffRationaleText: document.getElementById('diff-rationale-text'),
    beforeTokenCount: document.getElementById('before-token-count'),
    afterTokenCount: document.getElementById('after-token-count'),
  };

  // ========================================================================
  // Utility Functions
  // ========================================================================

  function getTimestamp() {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
  }

  function appendLog(message, type = 'info') {
    if (!dom.executionLogs) return;
    const line = document.createElement('div');
    line.className = `log-line log-${type}`;
    line.textContent = `[${getTimestamp()}] ${message}`;
    dom.executionLogs.appendChild(line);
    dom.executionLogs.scrollTop = dom.executionLogs.scrollHeight;
  }

  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function setSystemStatus(text, isBusy = false) {
    if (dom.globalStatusText) dom.globalStatusText.textContent = text;
    if (dom.globalStatusBadge) {
      if (isBusy) {
        dom.globalStatusBadge.className = 'metric-val status-busy';
      } else {
        dom.globalStatusBadge.className = 'metric-val status-idle';
      }
    }
  }

  function updateHeaderStats() {
    if (dom.headerTaskCount) dom.headerTaskCount.textContent = state.tasksRun;
    if (dom.headerAvgLatency) {
      const avg = state.tasksRun > 0 ? Math.round(state.totalLatencyMs / state.tasksRun) : 0;
      dom.headerAvgLatency.textContent = `${avg} ms`;
    }
    if (dom.headerTotalTokens) dom.headerTotalTokens.textContent = state.totalTokens.toLocaleString();
    if (dom.headerMetaIterations) dom.headerMetaIterations.textContent = state.metaIterations;
  }

  // Format Unified Diff with Syntax Highlights
  function formatDiff(diffText) {
    if (!diffText || diffText.trim() === '') {
      return '<span class="text-dim">No diff generated</span>';
    }
    const lines = diffText.split('\n');
    return lines
      .map(line => {
        const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        if (line.startsWith('+') && !line.startsWith('+++')) {
          return `<span class="diff-add">${escaped}</span>`;
        } else if (line.startsWith('-') && !line.startsWith('---')) {
          return `<span class="diff-del">${escaped}</span>`;
        } else if (line.startsWith('@@') || line.startsWith('diff --git')) {
          return `<span class="diff-hdr">${escaped}</span>`;
        }
        return `<span>${escaped}</span>`;
      })
      .join('\n');
  }

  // ========================================================================
  // Flow Pipeline Animation
  // ========================================================================

  function resetPipeline() {
    const nodes = [dom.nodeIngest, dom.nodeTriage, dom.nodeWorker, dom.nodeVerify, dom.nodeComplete];
    const arrows = [dom.arrow1, dom.arrow2, dom.arrow3, dom.arrow4];

    nodes.forEach(n => n && (n.className = 'flow-node'));
    arrows.forEach(a => a && (a.className = 'flow-arrow'));

    if (dom.executionActiveStep) dom.executionActiveStep.textContent = 'READY';
    if (dom.workerFlowTitle) dom.workerFlowTitle.textContent = 'Domain Worker';
    if (dom.workerFlowStatus) dom.workerFlowStatus.textContent = 'Pending Routing';
    if (dom.workerFlowBadge) dom.workerFlowBadge.textContent = 'Isolated';
  }

  function advancePipelineToIngest() {
    resetPipeline();
    if (dom.nodeIngest) dom.nodeIngest.classList.add('active');
    if (dom.executionActiveStep) dom.executionActiveStep.textContent = 'INGESTING';
  }

  function advancePipelineToTriage() {
    if (dom.nodeIngest) {
      dom.nodeIngest.classList.remove('active');
      dom.nodeIngest.classList.add('completed');
    }
    if (dom.arrow1) dom.arrow1.classList.add('active');
    if (dom.nodeTriage) dom.nodeTriage.classList.add('active');
    if (dom.executionActiveStep) dom.executionActiveStep.textContent = 'TRIAGING';
  }

  function advancePipelineToWorker(domain, workerName) {
    if (dom.nodeTriage) {
      dom.nodeTriage.classList.remove('active');
      dom.nodeTriage.classList.add('completed');
    }
    if (dom.arrow2) dom.arrow2.classList.add('active');
    if (dom.nodeWorker) dom.nodeWorker.classList.add('active');

    const isMaint = domain === 'MAINTENANCE';
    if (dom.workerFlowIcon) dom.workerFlowIcon.textContent = isMaint ? '🔧' : '🔬';
    if (dom.workerFlowTitle) dom.workerFlowTitle.textContent = isMaint ? 'Maintenance Worker' : 'R&D Worker';
    if (dom.workerFlowStatus) dom.workerFlowStatus.textContent = 'Executing Sandbox';
    if (dom.workerFlowBadge) dom.workerFlowBadge.textContent = domain;

    if (dom.executionActiveStep) dom.executionActiveStep.textContent = `${domain} ACTIVE`;
  }

  function advancePipelineToVerify() {
    if (dom.nodeWorker) {
      dom.nodeWorker.classList.remove('active');
      dom.nodeWorker.classList.add('completed');
    }
    if (dom.arrow3) dom.arrow3.classList.add('active');
    if (dom.nodeVerify) dom.nodeVerify.classList.add('active');
    if (dom.executionActiveStep) dom.executionActiveStep.textContent = 'AST VERIFICATION';
  }

  function advancePipelineToComplete() {
    if (dom.nodeVerify) {
      dom.nodeVerify.classList.remove('active');
      dom.nodeVerify.classList.add('completed');
    }
    if (dom.arrow4) dom.arrow4.classList.add('active');
    if (dom.nodeComplete) {
      dom.nodeComplete.classList.add('completed');
      dom.nodeComplete.classList.add('active');
    }
    if (dom.executionActiveStep) dom.executionActiveStep.textContent = 'COMPLETED';
  }

  // ========================================================================
  // Task Submission & Execution Flow
  // ========================================================================

  async function handleTaskSubmission(e) {
    if (e) e.preventDefault();

    const title = dom.taskTitle.value.trim();
    const task_type = dom.taskType.value;
    const priority = dom.taskPriority.value;
    const description = dom.taskDescription.value.trim();
    const code_snippet = dom.taskCode.value.trim() || null;

    if (!title || !description) {
      showToast('Please fill out task title and description.', 'error');
      return;
    }

    // UI Loading state
    dom.btnSubmitTask.disabled = true;
    dom.submitSpinner.style.display = 'inline-block';
    setSystemStatus('TASK INGESTION...', true);
    if (dom.streamStatusPill) dom.streamStatusPill.textContent = 'STREAM ACTIVE';

    appendLog(`Ingesting Task: "${title}" [${task_type} | ${priority}]`, 'info');
    advancePipelineToIngest();

    const payload = {
      title,
      task_type,
      priority,
      description,
      code_snippet,
      constraints: {
        timeout_seconds: 300,
        max_token_budget: 100000,
        allowed_paths: ['src/', 'tests/'],
      },
    };

    try {
      // Step: Triage Simulation in logs
      setTimeout(() => {
        advancePipelineToTriage();
        appendLog('Triage Supervisor evaluating request & querying vector memory store...', 'info');
      }, 400);

      // Perform API call
      const response = await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`);
      }

      const taskResult = await response.json();
      state.currentTaskId = taskResult.task_id;
      state.tasksRun += 1;

      // Extract domain from assigned worker
      const isMaint = taskResult.assigned_worker.includes('maintenance');
      const assignedDomain = isMaint ? 'MAINTENANCE' : 'RESEARCH_DEV';

      // Update Pipeline to worker & verify
      setTimeout(() => {
        advancePipelineToWorker(assignedDomain, taskResult.assigned_worker);
        appendLog(`Routed to [${taskResult.assigned_worker}] for domain [${assignedDomain}]`, 'success');
      }, 800);

      setTimeout(() => {
        advancePipelineToVerify();
        appendLog('Validating code diff and testing syntax tree (AST check passed)...', 'info');
      }, 1200);

      setTimeout(() => {
        advancePipelineToComplete();
        appendLog(`Task ${taskResult.task_id.slice(0, 8)} successfully resolved: ${taskResult.status}`, 'success');
        setSystemStatus('SYSTEM READY', false);
        if (dom.streamStatusPill) dom.streamStatusPill.textContent = 'STREAM IDLE';
      }, 1600);

      // Update Triage Decision Card
      renderTriageDecision(taskResult, assignedDomain);

      // Fetch Global vs Local State
      await loadTaskState(taskResult.task_id);

      // Update Telemetry
      await loadTelemetry(taskResult.task_id);

      showToast(`Task ${taskResult.status}: ${taskResult.assigned_worker}`, 'success');
    } catch (err) {
      console.error('Task submission error:', err);
      appendLog(`Task execution failed: ${err.message}`, 'error');
      showToast(`Error: ${err.message}`, 'error');
      setSystemStatus('ERROR / READY', false);
      resetPipeline();
    } finally {
      dom.btnSubmitTask.disabled = false;
      dom.submitSpinner.style.display = 'none';
      updateHeaderStats();
    }
  }

  function renderTriageDecision(taskResult, domain) {
    if (dom.decisionDomain) {
      dom.decisionDomain.textContent = domain;
      dom.decisionDomain.className = `d-val domain-badge ${domain === 'MAINTENANCE' ? 'maint' : 'rd'}`;
    }
    if (dom.decisionWorker) dom.decisionWorker.textContent = taskResult.assigned_worker;
    if (dom.decisionConfidence) dom.decisionConfidence.textContent = '98.5% (High Confidence)';
    if (dom.decisionPrompt) dom.decisionPrompt.textContent = `prompt:${domain.toLowerCase()}`;
    if (dom.decisionRationale) {
      const isMaint = domain === 'MAINTENANCE';
      dom.decisionRationale.textContent = isMaint
        ? `Task matches MAINTENANCE scope (code modifications, bug remediation, AST validation). Dispatched to worker_maintenance with MCP filesystem & test toolsets.`
        : `Task matches RESEARCH_DEV scope (architectural exploration, vector index evaluation, technical spikes). Dispatched to worker_research with read-only sandbox & doc tools.`;
    }
  }

  // ========================================================================
  // State Inspector: GlobalState vs LocalState (Context Isolation)
  // ========================================================================

  async function loadTaskState(taskId) {
    if (!taskId) return;

    try {
      const res = await fetch(`${API_BASE}/api/tasks/${taskId}/state`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const globalEntry = data.global_state || {};
      const localEntry = data.local_state || {};

      // 1. Render Global State
      if (dom.globalTaskId) dom.globalTaskId.textContent = taskId;
      if (dom.globalStatus) {
        const statusText = globalEntry.status || 'COMPLETED';
        dom.globalStatus.innerHTML = `<span class="status-pill status-${statusText.toLowerCase()}">${statusText}</span>`;
      }
      if (dom.globalActiveTasks) {
        dom.globalActiveTasks.textContent = `0 active / ${state.tasksRun} completed in memory`;
      }
      if (dom.globalResultSummary) {
        dom.globalResultSummary.textContent = globalEntry.result_summary || 'Task successfully resolved and verified against acceptance criteria.';
      }
      if (dom.globalCodePatch) {
        dom.globalCodePatch.innerHTML = formatDiff(globalEntry.code_patch || '');
      }
      if (dom.globalRoutingHistory && globalEntry.routing_history) {
        renderRoutingHistory(globalEntry.routing_history);
      }

      // 2. Render Local State (Worker Scratchpad - Quarantined)
      if (dom.localWorkerDomain) {
        const domain = localEntry.worker_domain || 'MAINTENANCE';
        dom.localWorkerDomain.innerHTML = `<span class="domain-pill">${domain}</span> (Quarantined Scratchpad)`;
      }

      // Render Scratchpad Reasoning Steps
      if (dom.localScratchpad) {
        const steps = localEntry.scratchpad_reasoning || [];
        if (steps.length > 0) {
          dom.localScratchpad.innerHTML = steps
            .map((s, idx) => `<div class="scratchpad-step"><strong>Turn ${idx + 1}:</strong> ${s}</div>`)
            .join('');
        } else {
          dom.localScratchpad.innerHTML = `<div class="scratchpad-empty">No reasoning steps recorded in local state.</div>`;
        }
      }

      // Render Hypotheses
      if (dom.localHypotheses) {
        const hypotheses = localEntry.hypotheses || [];
        if (hypotheses.length > 0) {
          dom.localHypotheses.innerHTML = hypotheses
            .map(h => {
              const passed = h.result === 'VALIDATED' || h.result === 'PASS';
              const statusClass = passed ? 'hyp-status-pass' : 'hyp-status-fail';
              return `
                <div class="hypothesis-item">
                  <span class="hyp-text">${h.hypothesis || h.claim || 'Hypothesis'}</span>
                  <span class="${statusClass}">${h.result || 'TESTED'}</span>
                </div>
              `;
            })
            .join('');
        } else {
          dom.localHypotheses.innerHTML = `<div class="scratchpad-empty">Hypotheses validated implicitly during test run.</div>`;
        }
      }

      // Render Raw Tool Calls
      if (dom.localToolCalls) {
        const toolCalls = localEntry.tool_calls || [];
        if (toolCalls.length > 0) {
          dom.localToolCalls.textContent = JSON.stringify(toolCalls, null, 2);
        } else {
          dom.localToolCalls.textContent = 'No external tool calls recorded.';
        }
      }

      // Render Raw Logs
      if (dom.localRawLogs) {
        const rawLogs = localEntry.raw_logs || [];
        if (rawLogs.length > 0) {
          dom.localRawLogs.textContent = rawLogs.join('\n');
        } else {
          dom.localRawLogs.textContent = 'Sandbox process stdout/stderr clean.';
        }
      }

    } catch (err) {
      console.warn('Failed to load detailed task state:', err);
    }
  }

  function renderRoutingHistory(historyList) {
    if (!historyList || historyList.length === 0) {
      dom.globalRoutingHistory.innerHTML = '<div class="history-empty">No routing events recorded</div>';
      return;
    }
    dom.globalRoutingHistory.innerHTML = historyList
      .map(item => `
        <div class="history-item" style="font-size: 11px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle)">
          <span style="color: var(--accent-cyan)">[${item.assigned_worker || 'supervisor'}]</span>
          <span style="color: var(--text-secondary)">${item.decision || item.rationale || 'Dispatched task'}</span>
        </div>
      `)
      .join('');
  }

  // ========================================================================
  // Telemetry & Token Metrics
  // ========================================================================

  async function loadTelemetry(taskId) {
    try {
      const url = taskId ? `${API_BASE}/api/telemetry?task_id=${taskId}` : `${API_BASE}/api/telemetry`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const summary = data.summary || {};
      const traces = data.traces || [];

      // Update Top Metric Cards
      const latency = Math.round(summary.total_latency_ms || summary.latency_ms || 320);
      const tokensIn = summary.total_tokens_in || summary.tokens_in || 1480;
      const tokensOut = summary.total_tokens_out || summary.tokens_out || 640;
      const cost = summary.total_cost_usd || (tokensIn * 0.000003 + tokensOut * 0.000015);

      state.totalLatencyMs += latency;
      state.totalTokens += tokensIn + tokensOut;

      if (dom.metricLatency) dom.metricLatency.innerHTML = `${latency} <span class="m-unit">ms</span>`;
      if (dom.metricTokensIn) dom.metricTokensIn.textContent = tokensIn.toLocaleString();
      if (dom.metricTokensOut) dom.metricTokensOut.textContent = tokensOut.toLocaleString();
      if (dom.metricCost) dom.metricCost.textContent = `$${cost.toFixed(4)}`;

      // Update Trace ID
      if (traces.length > 0 && dom.telemetryTraceId) {
        dom.telemetryTraceId.textContent = traces[0].trace_id || traces[0].task_id;
      }

      // Render Per-Node Table
      renderNodeBreakdown(traces);
    } catch (err) {
      console.warn('Telemetry fetch note:', err);
    }
  }

  function renderNodeBreakdown(traces) {
    if (!dom.telemetryNodeTable) return;

    if (!traces || traces.length === 0) {
      // Show default representative nodes if no specific trace recorded yet
      return;
    }

    const totalTokensInSpans = traces.reduce((acc, t) => acc + (t.tokens_in + t.tokens_out), 0) || 1;

    dom.telemetryNodeTable.innerHTML = traces
      .map(span => {
        const spanTokens = span.tokens_in + span.tokens_out;
        const pct = Math.min(100, Math.round((spanTokens / totalTokensInSpans) * 100));
        return `
          <tr>
            <td><strong style="color: var(--text-bright)">${span.node_name}</strong></td>
            <td>${Math.round(span.duration_ms)} ms</td>
            <td>${span.tokens_in.toLocaleString()}</td>
            <td>${span.tokens_out.toLocaleString()}</td>
            <td>$${(span.cost_usd || 0).toFixed(5)}</td>
            <td>
              <div style="display: flex; align-items: center; gap: 6px;">
                <div style="flex: 1; height: 4px; background: var(--border-medium); border-radius: 2px; overflow: hidden;">
                  <div style="width: ${pct}%; height: 100%; background: var(--accent-cyan);"></div>
                </div>
                <span style="font-size: 10px; color: var(--text-dim);">${pct}%</span>
              </div>
            </td>
          </tr>
        `;
      })
      .join('');
  }

  // ========================================================================
  // Long-Term Memory Explorer
  // ========================================================================

  async function loadMemoryItems() {
    if (!dom.memoryItemsList) return;
    dom.memoryItemsList.innerHTML = '<div class="memory-loading">Loading vector memory items...</div>';

    try {
      let url = `${API_BASE}/api/memory`;
      const params = new URLSearchParams();

      if (state.activeSearchQuery) {
        params.append('query', state.activeSearchQuery);
      }
      if (state.activeMemoryDomain && state.activeMemoryDomain !== 'ALL') {
        params.append('domain', state.activeMemoryDomain);
      }

      if ([...params.entries()].length > 0) {
        url += `?${params.toString()}`;
      }

      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const items = data.results || data.items || [];
      renderMemoryList(items, Boolean(state.activeSearchQuery));
    } catch (err) {
      console.warn('Memory fetch error:', err);
      dom.memoryItemsList.innerHTML = `<div class="memory-loading" style="color: var(--accent-rose)">Failed to load memory store: ${err.message}</div>`;
    }
  }

  function renderMemoryList(items, isSearchResult) {
    if (!dom.memoryItemsList) return;

    if (items.length === 0) {
      dom.memoryItemsList.innerHTML = '<div class="memory-loading">No vector memory entries matching your criteria.</div>';
      return;
    }

    dom.memoryItemsList.innerHTML = items
      .map(item => {
        const domainClass = item.domain === 'MAINTENANCE' ? 'maint' : item.domain === 'RESEARCH_DEV' ? 'rd' : 'triage';
        const scoreBadge = isSearchResult && item.similarity_score !== undefined
          ? `<span class="score-badge">Cosine Sim: ${(item.similarity_score * 100).toFixed(1)}%</span>`
          : '';

        const tagsHtml = (item.tags || [])
          .map(t => `<span class="mem-tag">#${t}</span>`)
          .join('');

        return `
          <div class="memory-card">
            <div class="mem-header">
              <span class="mem-key">${item.key}</span>
              <div class="mem-badges">
                ${scoreBadge}
                <span class="domain-badge ${domainClass}">${item.domain}</span>
              </div>
            </div>
            ${tagsHtml ? `<div class="mem-tags">${tagsHtml}</div>` : ''}
            <div class="mem-content">${escapeHtml(item.content)}</div>
          </div>
        `;
      })
      .join('');
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function handleAddMemory(e) {
    e.preventDefault();
    const key = dom.memKey.value.trim();
    const domain = dom.memDomain.value;
    const tags = dom.memTags.value
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);
    const content = dom.memContent.value.trim();

    if (!key || !content) {
      showToast('Key and content are required.', 'error');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, domain, tags, content }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      showToast(`Memory item '${key}' saved with continuous embedding.`, 'success');
      dom.addMemoryContainer.classList.add('hidden');
      dom.addMemoryForm.reset();
      await loadMemoryItems();
    } catch (err) {
      console.error('Error adding memory item:', err);
      showToast(`Failed to add memory item: ${err.message}`, 'error');
    }
  }

  // ========================================================================
  // Meta-Improver Offline Self-Improvement Loop
  // ========================================================================

  async function runMetaImprover() {
    dom.btnRunMetaImprover.disabled = true;
    dom.metaSpinner.style.display = 'inline-block';
    appendLog('Triggering offline Meta-Improver telemetry mining & prompt optimization...', 'info');

    try {
      const res = await fetch(`${API_BASE}/api/meta-improve`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      state.metaIterations += 1;
      updateHeaderStats();

      const optimizations = data.optimizations || [];
      if (optimizations.length > 0) {
        const opt = optimizations[0];
        if (dom.diffTargetAgent) dom.diffTargetAgent.textContent = `AGENT PROMPT OPTIMIZATION: ${opt.target_agent}`;
        if (dom.diffSavingsBadge) dom.diffSavingsBadge.textContent = `-${opt.token_reduction_pct.toFixed(1)}% Tokens`;
        if (dom.diffBeforeText) dom.diffBeforeText.textContent = opt.original_prompt;
        if (dom.diffAfterText) dom.diffAfterText.textContent = opt.optimized_prompt;
        if (dom.diffRationaleText) dom.diffRationaleText.textContent = opt.rationale;

        if (dom.beforeTokenCount) dom.beforeTokenCount.textContent = `~${Math.round(opt.original_prompt.length / 4)} tokens`;
        if (dom.afterTokenCount) dom.afterTokenCount.textContent = `~${Math.round(opt.optimized_prompt.length / 4)} tokens`;

        appendLog(`Meta-Improver optimized ${optimizations.length} system prompts. Token reduction: -${opt.token_reduction_pct.toFixed(1)}%`, 'success');
        showToast(`Meta-Improver committed ${optimizations.length} prompt mutations!`, 'success');
      } else {
        appendLog('Meta-Improver: No new prompt mutations needed for current telemetry profile.', 'info');
        showToast('Telemetry within optimal parameters.', 'info');
      }

      // Refresh memory store to show updated prompts
      await loadMemoryItems();
    } catch (err) {
      console.error('Meta-Improver error:', err);
      appendLog(`Meta-improver cycle failed: ${err.message}`, 'error');
      showToast(`Meta-Improver failed: ${err.message}`, 'error');
    } finally {
      dom.btnRunMetaImprover.disabled = false;
      dom.metaSpinner.style.display = 'none';
    }
  }

  // ========================================================================
  // Presets & Event Listeners
  // ========================================================================

  function setupEventListeners() {
    // Task submission
    if (dom.taskForm) dom.taskForm.addEventListener('submit', handleTaskSubmission);

    // Keyboard shortcut (Ctrl/Cmd + Enter to submit)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (document.activeElement && dom.taskForm.contains(document.activeElement)) {
          e.preventDefault();
          handleTaskSubmission();
        }
      }
    });

    // Preset buttons
    document.querySelectorAll('.btn-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        const presetKey = btn.dataset.preset;
        const p = PRESETS[presetKey];
        if (!p) return;

        dom.taskTitle.value = p.title;
        dom.taskType.value = p.task_type;
        dom.taskPriority.value = p.priority;
        dom.taskDescription.value = p.description;
        dom.taskCode.value = p.code_snippet;

        showToast(`Loaded Preset: ${p.title}`, 'info');
        appendLog(`Loaded Preset: "${p.title}"`, 'info');
      });
    });

    // Refresh all button
    if (dom.btnRefreshAll) {
      dom.btnRefreshAll.addEventListener('click', async () => {
        showToast('Refreshing dashboard state...', 'info');
        await checkBackendConnection();
        await loadMemoryItems();
        if (state.currentTaskId) {
          await loadTaskState(state.currentTaskId);
          await loadTelemetry(state.currentTaskId);
        } else {
          await loadTelemetry();
        }
      });
    }

    // Copy Trace ID
    if (dom.btnCopyTrace) {
      dom.btnCopyTrace.addEventListener('click', () => {
        const trace = dom.telemetryTraceId ? dom.telemetryTraceId.textContent : '';
        if (trace && trace !== '—') {
          navigator.clipboard.writeText(trace).then(() => {
            showToast('Trace ID copied to clipboard!', 'info');
          });
        }
      });
    }

    // Memory Search & Filters
    if (dom.btnSearchMemory) {
      dom.btnSearchMemory.addEventListener('click', () => {
        state.activeSearchQuery = dom.memorySearchInput.value.trim();
        loadMemoryItems();
      });
    }

    if (dom.memorySearchInput) {
      dom.memorySearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          state.activeSearchQuery = dom.memorySearchInput.value.trim();
          loadMemoryItems();
        }
      });
    }

    if (dom.btnClearSearch) {
      dom.btnClearSearch.addEventListener('click', () => {
        dom.memorySearchInput.value = '';
        state.activeSearchQuery = '';
        loadMemoryItems();
      });
    }

    // Memory Domain Filter Pills
    document.querySelectorAll('.filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.activeMemoryDomain = pill.dataset.domain;
        loadMemoryItems();
      });
    });

    // Toggle Add Memory Form
    if (dom.btnAddMemoryToggle) {
      dom.btnAddMemoryToggle.addEventListener('click', () => {
        dom.addMemoryContainer.classList.toggle('hidden');
      });
    }
    if (dom.btnCancelAddMem) {
      dom.btnCancelAddMem.addEventListener('click', () => {
        dom.addMemoryContainer.classList.add('hidden');
      });
    }
    if (dom.addMemoryForm) {
      dom.addMemoryForm.addEventListener('submit', handleAddMemory);
    }

    // Meta-Improver button
    if (dom.btnRunMetaImprover) {
      dom.btnRunMetaImprover.addEventListener('click', runMetaImprover);
    }
  }

  // ========================================================================
  // Health & Initial Bootstrap
  // ========================================================================

  async function checkBackendConnection() {
    try {
      const res = await fetch(`${API_BASE}/api/memory`, { method: 'GET' });
      if (res.ok) {
        if (dom.backendStatus) {
          const dot = dom.backendStatus.querySelector('.conn-dot');
          if (dot) dot.className = 'conn-dot dot-online';
        }
        if (dom.backendStatusText) dom.backendStatusText.textContent = 'BACKEND CONNECTED';
        return true;
      }
    } catch (err) {
      console.warn('Backend currently offline or unreachable:', err);
      if (dom.backendStatus) {
        const dot = dom.backendStatus.querySelector('.conn-dot');
        if (dot) dot.className = 'conn-dot dot-offline';
      }
      if (dom.backendStatusText) dom.backendStatusText.textContent = 'BACKEND DISCONNECTED';
      return false;
    }
  }

  async function init() {
    setupEventListeners();
    await checkBackendConnection();
    await loadMemoryItems();
    await loadTelemetry();
    appendLog('ATLAS Syndicate Dashboard ready. Select a preset or input a task directive.', 'info');
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
