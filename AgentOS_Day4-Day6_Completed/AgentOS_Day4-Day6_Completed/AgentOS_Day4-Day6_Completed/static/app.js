(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const output = $("terminal-output");
  const input = $("shell-input");
  const form = $("shell-form");
  const submitButton = $("submit-command");
  const schedulerSelect = $("scheduler-select");
  const state = { ws: null, wsConnected: false, tasks: [], blocked: [], metrics: null, seenResponses: new Set(), streamLines: new Map(), refreshing: false };

  function appendLine(kind, prefix, message) {
    const line = document.createElement("div");
    line.className = `term-line ${kind || ""}`;
    const p = document.createElement("span");
    p.className = "term-prefix";
    p.textContent = prefix;
    const content = document.createElement("span");
    content.className = "term-content";
    content.textContent = String(message ?? "");
    line.append(p, content);
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
  }

  function appendCommand(command) { appendLine("command", "›", command); }
  function printResult(message) { appendLine("response", "◆", message); }
  function printSystem(message) { appendLine("system", "◈", message); }
  function printError(message) { appendLine("error", "!", message); }
  function shortText(value, max = 92) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  }
  function formatTime(value) {
    if (!value) return "just now";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  function formatNumber(value, decimals = 0) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.error || `Request failed (${response.status})`);
    return data;
  }

  function statusClass(status) {
    const value = String(status || "queued").toLowerCase();
    if (value === "done" || value === "completed" || value === "success") return "done";
    if (value === "running" || value === "in_progress") return "running";
    if (value === "failed" || value === "blocked") return value;
    return "queued";
  }

  function renderQueue(tasks = state.tasks) {
    const list = $("queue-list");
    list.replaceChildren();
    const items = [...tasks].sort((a, b) => {
      const rank = { running: 0, queued: 1, blocked: 2, failed: 2, done: 3 };
      return (rank[statusClass(a.status)] ?? 4) - (rank[statusClass(b.status)] ?? 4) || new Date(b.submitted_at || 0) - new Date(a.submitted_at || 0);
    }).slice(0, 12);
    $("queue-count").textContent = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;
    if (!items.length) {
      const empty = document.createElement("div"); empty.className = "empty-state";
      empty.innerHTML = "<span>◇</span><p>No tasks yet</p><small>Submit a request in the AI shell.</small>";
      list.appendChild(empty); return;
    }
    for (const task of items) {
      const item = document.createElement("div"); item.className = "queue-item";
      const stateBar = document.createElement("div"); stateBar.className = `queue-state ${statusClass(task.status)}`;
      const main = document.createElement("div"); main.className = "queue-main";
      const prompt = document.createElement("div"); prompt.className = "queue-prompt"; prompt.textContent = shortText(task.prompt || task.task?.prompt || "Task", 100); prompt.title = task.prompt || task.task?.prompt || "";
      const meta = document.createElement("div"); meta.className = "queue-meta";
      const agent = document.createElement("span"); agent.textContent = task.agent || task.result?.agent || task.task?.agent_type || "Agent pending";
      const scheduler = document.createElement("span"); scheduler.textContent = task.scheduler || "FIFO";
      const time = document.createElement("span"); time.textContent = formatTime(task.submitted_at || task.task?.submitted_at);
      meta.append(agent, scheduler, time); main.append(prompt, meta);
      const right = document.createElement("div"); right.style.display = "grid"; right.style.justifyItems = "end"; right.style.gap = "6px";
      const tag = document.createElement("span"); tag.className = `status-tag ${statusClass(task.status)}`; tag.textContent = task.status || "queued";
      const priority = document.createElement("span"); priority.className = "queue-priority"; priority.textContent = `P${task.task?.priority ?? task.priority ?? 5}`;
      right.append(tag, priority); item.append(stateBar, main, right); list.appendChild(item);
    }
  }

  function renderBlocked(items = state.blocked) {
    const list = $("blocked-list"); list.replaceChildren();
    $("blocked-count").textContent = `${items.length} DENIED`;
    if (!items.length) {
      const empty = document.createElement("div"); empty.className = "empty-state compact";
      empty.innerHTML = "<span>✓</span><p>No blocked actions recorded</p><small>Denied policy calls will appear here.</small>";
      list.appendChild(empty); return;
    }
    for (const action of items.slice(0, 12)) {
      const card = document.createElement("div"); card.className = "blocked-item";
      const head = document.createElement("div"); head.className = "blocked-head";
      const title = document.createElement("span"); title.textContent = action.action || "Denied operation";
      const time = document.createElement("span"); time.className = "blocked-time"; time.textContent = formatTime(action.timestamp);
      head.append(title, time);
      const reason = document.createElement("div"); reason.className = "blocked-reason"; reason.textContent = action.reason || "Denied by server-side policy";
      const agent = document.createElement("div"); agent.className = "blocked-agent"; agent.textContent = `${action.agent || "Unknown agent"}${action.task_id ? ` · task ${String(action.task_id).slice(0, 8)}` : ""}`;
      card.append(head, reason, agent); list.appendChild(card);
    }
  }

  function renderMetrics(metrics) {
    state.metrics = metrics;
    $("cpu-value").textContent = formatNumber(metrics.cpu_percent, 1);
    $("ram-value").textContent = formatNumber(metrics.ram_percent, 1);
    $("ram-caption").textContent = metrics.ram_used_mb == null ? "Host RAM utilization" : `${formatNumber(metrics.ram_used_mb)} MB in use`;
    $("cpu-meter").style.width = `${Math.max(0, Math.min(100, Number(metrics.cpu_percent) || 0))}%`;
    $("ram-meter").style.width = `${Math.max(0, Math.min(100, Number(metrics.ram_percent) || 0))}%`;
    $("token-value").textContent = formatNumber(metrics.tokens_total ?? metrics.tokens);
    $("overview-tokens").textContent = formatNumber(metrics.tokens_total ?? metrics.tokens);
    $("latency-value").textContent = metrics.latency_seconds == null ? "—" : formatNumber(metrics.latency_seconds, 2);
    $("overview-queue").textContent = formatNumber(metrics.queue_length);
    $("done-value").textContent = formatNumber(metrics.tasks_done);
    $("overview-scheduler").textContent = metrics.scheduler || "FIFO";
    $("backend-value").textContent = metrics.llm_backend || "—";
    $("model-value").textContent = metrics.model || "Qwen2.5 · 1.5B";
    if (metrics.scheduler) {
      const current = schedulerSelect.value;
      const normalized = metrics.scheduler === "RR" ? "rr" : metrics.scheduler === "Priority" ? "priority" : metrics.scheduler === "AgentOS" ? "agentos" : "fifo";
      if (current !== normalized && !schedulerSelect.dataset.busy) schedulerSelect.value = normalized;
    }
    $("last-refresh").textContent = `UPDATED ${new Date().toLocaleTimeString()}`;
  }

  async function refreshDashboard() {
    if (state.refreshing) return;
    state.refreshing = true;
    try {
      const [metrics, history, blocked, status] = await Promise.all([
        api("/metrics"), api("/history?limit=100"), api("/blocked?limit=100"), api("/api/status")
      ]);
      renderMetrics(metrics);
      state.tasks = history.tasks || [];
      state.blocked = blocked.blocked_actions || [];
      renderQueue(state.tasks);
      renderBlocked(state.blocked);
      $("overview-agents").textContent = formatNumber(status.agents);
      $("system-status").textContent = "System Online";
      $("system-dot").className = "status-dot online";
    } catch (error) {
      $("system-status").textContent = "API Unavailable";
      $("system-dot").className = "status-dot offline";
      $("last-refresh").textContent = "API CONNECTION ERROR";
    } finally { state.refreshing = false; }
  }

  function showHistory() {
    if (!state.tasks.length) { printResult("No task history has been recorded yet."); return; }
    printResult(`SQLite history · ${state.tasks.length} recent task(s)`);
    for (const task of state.tasks.slice(0, 10)) {
      appendLine("system", "·", `${task.status} | ${task.agent} | ${task.scheduler} | ${shortText(task.prompt, 72)}${task.latency_seconds != null ? ` | ${Number(task.latency_seconds).toFixed(2)}s` : ""}`);
    }
  }

  async function showStatus() {
    const [metrics, status] = await Promise.all([api("/metrics"), api("/api/status")]);
    printResult(`AgentOS ${status.status} · backend ${metrics.llm_backend} · model ${metrics.model}`);
    printSystem(`scheduler=${metrics.scheduler} queue=${metrics.queue_length} cpu=${formatNumber(metrics.cpu_percent, 1)}% ram=${formatNumber(metrics.ram_percent, 1)}% tokens=${metrics.tokens_total} completed=${metrics.tasks_done}`);
  }

  async function switchScheduler(value) {
    schedulerSelect.dataset.busy = "1";
    try {
      const data = await api("/scheduler", { method: "POST", body: JSON.stringify({ scheduler: value }) });
      schedulerSelect.value = value;
      printSystem(`Scheduler changed to ${data.scheduler}. ${data.queued_preserved} queued task(s) preserved.`);
      $("scheduler-note").textContent = `Active: ${data.scheduler}`;
      await refreshDashboard();
    } catch (error) {
      printError(`Could not change scheduler: ${error.message}`);
      await refreshDashboard();
    } finally { delete schedulerSelect.dataset.busy; }
  }

  function help() {
    printResult("Built-in commands:");
    appendLine("system", "·", "help — show this help");
    appendLine("system", "·", "status — runtime, CPU, RAM, queue and token metrics");
    appendLine("system", "·", "history — show recent SQLite task history");
    appendLine("system", "·", "scheduler <fifo|rr|priority|agentos> — switch scheduler live");
    appendLine("system", "·", "run <request> — submit a task to AgentOS");
    appendLine("system", "·", "Any other text is sent as a task request. Shell commands are never sent to bash.");
  }

  async function submitTask(prompt) {
    if (!prompt.trim()) return;
    submitButton.disabled = true;
    try {
      const data = await api("/task", { method: "POST", body: JSON.stringify({ prompt: prompt.trim(), priority: 5, estimated_tokens: 256, complexity: 1, risk_level: 1 }) });
      printSystem(`Task submitted · ${data.task_id} · ${data.agent} · scheduler ${data.scheduler}`);
      if (!state.wsConnected) printSystem("Live stream is reconnecting; task status will refresh from SQLite history.");
      await refreshDashboard();
    } catch (error) {
      printError(`Task submission failed: ${error.message}`);
    } finally {
      submitButton.disabled = false;
      input.focus();
    }
  }

  async function executeCommand(raw) {
    const command = raw.trim();
    if (!command) return;
    appendCommand(command);
    const firstSpace = command.indexOf(" ");
    const verb = (firstSpace < 0 ? command : command.slice(0, firstSpace)).toLowerCase();
    const rest = firstSpace < 0 ? "" : command.slice(firstSpace + 1).trim();
    if (verb === "help" && !rest) { help(); return; }
    if (verb === "status" && !rest) {
      try { await showStatus(); } catch (error) { printError(error.message); }
      return;
    }
    if (verb === "history" && !rest) { await refreshDashboard(); showHistory(); return; }
    if (verb === "scheduler") {
      if (!rest) { printResult(`Current scheduler: ${state.metrics?.scheduler || "loading"}. Options: fifo, rr, priority, agentos.`); return; }
      const value = rest.toLowerCase();
      if (!["fifo", "rr", "priority", "agentos"].includes(value)) { printError("Usage: scheduler <fifo|rr|priority|agentos>"); return; }
      await switchScheduler(value); return;
    }
    if (verb === "run") {
      if (!rest) { printError("Usage: run <request>"); return; }
      await submitTask(rest); return;
    }
    // Intentionally no shell execution path: all non-built-in text becomes an
    // AgentOS task request and is validated/enforced by the FastAPI backend.
    await submitTask(command);
  }

  function connectStream() {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${scheme}//${location.host}/stream`);
    state.ws = ws;
    ws.onopen = () => {
      state.wsConnected = true;
      $("shell-connection").textContent = "WS CONNECTED";
      $("shell-connection").style.color = "var(--green)";
    };
    ws.onmessage = (message) => {
      let event;
      try { event = JSON.parse(message.data); } catch { return; }
      if (event.type === "connected") return;
      if (event.type === "task_update") {
        if (event.status === "running") printSystem(`Task ${String(event.task_id).slice(0, 8)} is running on ${event.agent || "agent"} (${event.scheduler}).`);
        if (["done", "failed", "blocked"].includes(event.status) && event.result) {
          if (!state.seenResponses.has(event.task_id)) {
            state.seenResponses.add(event.task_id);
            const result = event.result;
            const label = `${event.status.toUpperCase()} · ${event.agent || "Agent"} · ${result.tokens_used || 0} tokens`;
            appendLine(event.status === "done" ? "response" : "error", event.status === "done" ? "◆" : "!", label);
            const streamedLine = state.streamLines.has(event.task_id);
            if (result.response && !streamedLine) appendLine("response", "│", result.response);
            if (streamedLine) state.streamLines.delete(event.task_id);
            if (result.error) appendLine("error", "│", result.error);
          }
        }
        refreshDashboard();
      } else if (event.type === "token_chunk") {
        let content = state.streamLines.get(event.task_id);
        if (!content) {
          const line = document.createElement("div"); line.className = "term-line response";
          const prefix = document.createElement("span"); prefix.className = "term-prefix"; prefix.textContent = "│";
          content = document.createElement("span"); content.className = "term-content";
          line.append(prefix, content); output.appendChild(line); state.streamLines.set(event.task_id, content);
        }
        content.textContent += event.chunk || "";
        output.scrollTop = output.scrollHeight;
      } else if (event.type === "token_update") {
        printSystem(`Task ${String(event.task_id).slice(0, 8)} completed with ${event.tokens_used || 0} reported tokens.`);
        refreshDashboard();
      } else if (event.type === "blocked_action") {
        printError(`Policy denied ${event.action || "an operation"}: ${event.reason || "blocked by policy"}`);
        refreshDashboard();
      } else if (event.type === "scheduler_update") {
        printSystem(`Scheduler is now ${event.scheduler}.`); refreshDashboard();
      }
    };
    ws.onclose = () => {
      state.wsConnected = false;
      $("shell-connection").textContent = "WS RECONNECTING";
      $("shell-connection").style.color = "var(--amber)";
      setTimeout(connectStream, 1800);
    };
    ws.onerror = () => { try { ws.close(); } catch { /* ignore */ } };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const command = input.value;
    input.value = "";
    await executeCommand(command);
  });
  $("clear-terminal").addEventListener("click", () => { output.replaceChildren(); printSystem("Terminal display cleared. Task history remains in SQLite."); });
  schedulerSelect.addEventListener("change", () => switchScheduler(schedulerSelect.value));
  function tickClock() { $("clock").textContent = new Date().toLocaleTimeString([], { hour12: false }); }
  tickClock(); setInterval(tickClock, 1000);
  connectStream(); refreshDashboard(); setInterval(refreshDashboard, 2500);
})();
