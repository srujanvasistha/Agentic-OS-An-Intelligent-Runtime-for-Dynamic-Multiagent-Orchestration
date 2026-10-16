import { useState } from "react";
import {
  Cpu,
  Layers,
  ArrowRight,
  Play,
  RotateCw,
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  Clock,
  Sparkles,
  Zap,
  BarChart,
  Eye,
} from "lucide-react";
import { playCyberClick, playSuccessSound, playAlertSound } from "../utils/audio";

export default function SchedulerView({
  scheduler = "fifo",
  onSwitchScheduler,
  tasks = [],
  api,
  onRefresh,
  onInspectTask,
  metrics,
}) {
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [stepping, setStepping] = useState(false);
  const [stepResult, setStepResult] = useState(null);

  const schedulerAlgorithms = [
    {
      id: "fifo",
      name: "FIFO (First In First Out)",
      tagline: "Sequential Execution",
      desc: "Executes tasks strictly in order of submission timestamp. Minimal overhead, predictable ordering.",
      badge: "Standard",
      color: "border-cyan",
      accent: "#00f0ff",
    },
    {
      id: "priority",
      name: "Priority Scheduler",
      tagline: "Urgency-Weighted Queue",
      desc: "Orders tasks by priority weight (1-10). Critical security tasks and urgent requests preempt lower priority tasks.",
      badge: "Preemptive",
      color: "border-amber",
      accent: "#f59e0b",
    },
    {
      id: "roundrobin",
      name: "Round Robin",
      tagline: "Fair-Share Agent Rotation",
      desc: "Cycles through available agent workers evenly to prevent starvation across General, File, and Security agents.",
      badge: "Fair Share",
      color: "border-violet",
      accent: "#8b5cf6",
    },
    {
      id: "resourceaware",
      name: "Resource Aware",
      tagline: "Load & Memory Adaptive",
      desc: "Considers estimated token requirements and real-time host RAM/CPU pressure before dispatching heavy requests.",
      badge: "Adaptive",
      color: "border-emerald",
      accent: "#10b981",
    },
  ];

  const handleStep = async () => {
    setStepping(true);
    playCyberClick();
    try {
      const res = await api("/api/runtime/step", { method: "POST" });
      if (res.result) {
        setStepResult(`Executed task ${res.result.task_id.slice(0, 8)} (${res.result.status}) via ${res.result.scheduler || scheduler} in ${Number(res.result.latency_seconds).toFixed(2)}s`);
        playSuccessSound();
      } else {
        setStepResult("Queue is currently empty. No tasks to step.");
      }
      if (onRefresh) onRefresh();
    } catch (err) {
      setStepResult(`Step error: ${err.message}`);
      playAlertSound();
    } finally {
      setStepping(false);
    }
  };

  const handleRunAll = async () => {
    setStepping(true);
    playCyberClick();
    try {
      const res = await api("/api/runtime/run-all", { method: "POST" });
      if (res.executed_count > 0) {
        setStepResult(`Executed ${res.executed_count} queued tasks through ${res.scheduler} scheduler.`);
        playSuccessSound();
      } else {
        setStepResult("Queue is currently empty. Click 'Load Test Batch' to add tasks.");
      }
      if (onRefresh) onRefresh();
    } catch (err) {
      setStepResult(`Run error: ${err.message}`);
      playAlertSound();
    } finally {
      setStepping(false);
    }
  };

  const handleLoadDemoBatch = async () => {
    setStepping(true);
    playCyberClick();
    try {
      const res = await api("/api/queue/demo-batch", { method: "POST" });
      setStepResult(`Loaded 4 demo tasks (P2, P10, P6, P4) into ${res.scheduler} queue!`);
      playSuccessSound();
      if (onRefresh) onRefresh();
    } catch (err) {
      setStepResult(`Demo load error: ${err.message}`);
      playAlertSound();
    } finally {
      setStepping(false);
    }
  };

  const handleClearQueue = async () => {
    playCyberClick();
    try {
      await api("/api/queue/clear", { method: "POST" });
      setStepResult("Queue cleared.");
      playSuccessSound();
      if (onRefresh) onRefresh();
    } catch (err) {
      setStepResult(`Clear error: ${err.message}`);
      playAlertSound();
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const matchesStatus = filterStatus === "all" || t.status === filterStatus;
    const matchesSearch =
      !searchQuery ||
      t.prompt?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.agent_type?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const queuedCount = tasks.filter((t) => t.status === "queued").length;
  const doneCount = tasks.filter((t) => t.status === "done").length;
  const failedCount = tasks.filter((t) => t.status === "failed" || t.status === "blocked").length;

  return (
    <div className="scheduler-workspace">
      {/* Top Banner: Algorithm Matrix */}
      <section className="algorithm-matrix-section">
        <div className="section-header-title">
          <Layers size={18} className="text-cyan" />
          <div>
            <h2>Scheduler Policy Engine</h2>
            <p>Hot-swap operating scheduling policies. Tasks in queue automatically reorder upon policy change.</p>
          </div>
        </div>

        <div className="algo-cards-grid">
          {schedulerAlgorithms.map((algo) => {
            const isActive = scheduler.toLowerCase() === algo.id;
            return (
              <div
                key={algo.id}
                className={`algo-card glass-panel ${isActive ? "active-algo" : ""}`}
                style={{ "--accent-color": algo.accent }}
              >
                <div className="algo-card-top">
                  <span className="algo-badge">{algo.badge}</span>
                  {isActive && <span className="active-pill">ACTIVE POLICY</span>}
                </div>
                <h4 className="algo-name">{algo.name}</h4>
                <div className="algo-tagline">{algo.tagline}</div>
                <p className="algo-desc">{algo.desc}</p>
                <button
                  type="button"
                  className={`btn-algo-action ${isActive ? "is-active" : ""}`}
                  disabled={isActive}
                  onClick={() => {
                    playCyberClick();
                    onSwitchScheduler(algo.id);
                  }}
                >
                  {isActive ? "✓ Currently Active" : `Activate ${algo.badge}`}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Step Debugger & Pipeline Summary Strip */}
      <div className="pipeline-control-strip glass-panel">
        <div className="step-debugger-box">
          <div className="step-title-group">
            <Zap size={16} className="text-amber" />
            <div>
              <strong>Runtime Stepper & Batch Engine</strong>
              <span>Execute next task in queue tick-by-tick or batch run under active policy</span>
            </div>
          </div>
          <div className="step-actions" style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              className="btn-step"
              onClick={handleStep}
              disabled={stepping}
              title="Execute the next single task according to active scheduler"
            >
              {stepping ? <RotateCw size={13} className="spin" /> : <Play size={13} />}
              <span>Step (1 Task)</span>
            </button>

            <button
              type="button"
              className="btn-step"
              style={{ borderColor: "rgba(16, 185, 129, 0.4)", background: "rgba(16, 185, 129, 0.12)", color: "#10b981" }}
              onClick={handleRunAll}
              disabled={stepping}
              title="Execute all tasks in the queue until empty"
            >
              <Zap size={13} className="text-emerald" />
              <span>Run All Queue</span>
            </button>

            <button
              type="button"
              className="btn-step"
              style={{ borderColor: "rgba(0, 240, 255, 0.4)", background: "rgba(0, 240, 255, 0.12)", color: "#00f0ff" }}
              onClick={handleLoadDemoBatch}
              disabled={stepping}
              title="Load 4 test tasks with diverse priorities (P2, P10, P6, P4)"
            >
              <Sparkles size={13} className="text-cyan" />
              <span>🧪 Load Test Batch (4 Tasks)</span>
            </button>

            {queuedCount > 0 && (
              <button
                type="button"
                className="btn-step"
                style={{ borderColor: "rgba(244, 63, 94, 0.4)", background: "rgba(244, 63, 94, 0.12)", color: "#f43f5e" }}
                onClick={handleClearQueue}
                disabled={stepping}
                title="Clear all queued tasks"
              >
                <span>✕ Clear Queue</span>
              </button>
            )}

            {stepResult && <span className="step-status-tag">{stepResult}</span>}
          </div>
        </div>

        <div className="pipeline-counters">
          <div className="pipe-counter">
            <span className="pipe-label">QUEUED</span>
            <strong className="text-amber">{queuedCount}</strong>
          </div>
          <div className="pipe-counter">
            <span className="pipe-label">COMPLETED</span>
            <strong className="text-emerald">{doneCount}</strong>
          </div>
          <div className="pipe-counter">
            <span className="pipe-label">FAILED / BLOCKED</span>
            <strong className="text-rose">{failedCount}</strong>
          </div>
          <div className="pipe-counter">
            <span className="pipe-label">TOTAL LOGGED</span>
            <strong className="text-cyan">{tasks.length}</strong>
          </div>
        </div>
      </div>

      {/* Task Queue & History Matrix */}
      <section className="task-history-section glass-panel">
        <div className="table-controls-bar">
          <div className="search-box">
            <Search size={14} className="text-slate" />
            <input
              type="text"
              placeholder="Search tasks by prompt, ID, or agent..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-chips">
            {["all", "queued", "done", "failed", "blocked"].map((st) => (
              <button
                key={st}
                className={`filter-chip ${filterStatus === st ? "active" : ""}`}
                onClick={() => setFilterStatus(st)}
              >
                {st.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Task Table */}
        <div className="tasks-table-wrapper">
          {filteredTasks.length === 0 ? (
            <div className="empty-tasks-state">
              <Clock size={32} className="text-slate" />
              <h4>No matching tasks found</h4>
              <p>Submit tasks from the AI Shell to see scheduler dispatch records.</p>
            </div>
          ) : (
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>STATUS</th>
                  <th>TASK PROMPT</th>
                  <th>AGENT TYPE</th>
                  <th>PRIORITY</th>
                  <th>TOKENS</th>
                  <th>LATENCY</th>
                  <th>TIME</th>
                  <th>INSPECT</th>
                </tr>
              </thead>
              <tbody>
                {filteredTasks.map((t) => (
                  <tr key={t.id} className="task-row-item">
                    <td>
                      <span className={`status-badge-cell badge-${t.status}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="prompt-cell" title={t.prompt}>
                      <strong>{t.prompt?.slice(0, 50)}…</strong>
                      <span className="task-sub-id">{t.id.slice(0, 8)}</span>
                    </td>
                    <td>
                      <span className="agent-tag-cell">{t.agent_type || "Auto"}</span>
                    </td>
                    <td>
                      <span className="priority-tag-cell">P{t.priority ?? 5}</span>
                    </td>
                    <td>{t.estimated_tokens || 256}</td>
                    <td>{t.latency_seconds ? `${Number(t.latency_seconds).toFixed(2)}s` : "—"}</td>
                    <td>
                      <small>
                        {t.completed_at
                          ? new Date(t.completed_at).toLocaleTimeString()
                          : t.submitted_at
                          ? new Date(t.submitted_at).toLocaleTimeString()
                          : "—"}
                      </small>
                    </td>
                    <td>
                      <button
                        className="btn-inspect-task"
                        onClick={() => onInspectTask(t)}
                        title="Open task inspector"
                      >
                        <Eye size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
