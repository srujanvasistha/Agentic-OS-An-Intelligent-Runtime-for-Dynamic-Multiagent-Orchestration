import { useCallback, useEffect, useState } from "react";
import Header from "./components/Header";
import AiShellView from "./components/AiShellView";
import SchedulerView from "./components/SchedulerView";
import AgentsView from "./components/AgentsView";
import TelemetryView from "./components/TelemetryView";
import ResultsView from "./components/ResultsView";
import TaskModal from "./components/TaskModal";
import Hyperspace from "./components/originkit/ui/hyperspace-custom-style";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ??
  (window.location.port === "5173" ? "http://127.0.0.1:8000" : "");

const WS_URL =
  import.meta.env.VITE_WS_URL ??
  (window.location.port === "5173"
    ? "ws://127.0.0.1:8000/stream"
    : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/stream`);

async function api(path, options = {}) {
  const url = `${API_URL}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : data.detail?.detail;
    throw new Error(detail || data.error || `Request failed (${response.status})`);
  }
  return data;
}

export default function App() {
  const [tab, setTab] = useState("shell");
  const [online, setOnline] = useState(false);
  const [stats, setStats] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [blocked, setBlocked] = useState([]);
  const [figures, setFigures] = useState([]);
  const [scheduler, setScheduler] = useState("fifo");
  const [inspectingTask, setInspectingTask] = useState(null);
  const [events, setEvents] = useState([]);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  // Refresh primary runtime data
  const refresh = useCallback(async () => {
    try {
      const [statusData, metricsData, agentData, historyData, blockedData] = await Promise.all([
        api("/api/status"),
        api("/metrics"),
        api("/api/agents/details").catch(() => api("/api/agents/status")),
        api("/history"),
        api("/blocked"),
      ]);

      setStats(statusData);
      setMetrics(metricsData);
      setAgents(agentData.agents || []);
      setTasks([...(historyData.tasks || [])].reverse());
      setBlocked(blockedData.blocked_actions || []);
      setScheduler(
        (statusData.scheduler || "FIFOScheduler").toLowerCase().replace("scheduler", "")
      );
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  // Refresh research figures
  const refreshFigures = useCallback(async () => {
    try {
      const data = await api("/api/results/figures");
      setFigures(data.figures || []);
    } catch {
      // Figures may be ungenerated initially
    }
  }, []);

  // Periodic polling fallback
  useEffect(() => {
    refresh();
    refreshFigures();
    const interval = setInterval(refresh, 2500);
    return () => clearInterval(interval);
  }, [refresh, refreshFigures]);

  // WebSocket Live Stream Connection
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          setOnline(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setEvents((prev) => [...prev.slice(-40), data]);

            if (data.type === "task_updated") {
              refresh();
              if (data.status === "done") {
                showToast(`Task ${data.task_id?.slice(0, 8)} completed successfully!`, "success");
              } else if (data.status === "failed" || data.status === "blocked") {
                showToast(`Task ${data.task_id?.slice(0, 8)} ${data.status}`, "warning");
              }
            } else if (data.type === "task_queued") {
              refresh();
              showToast(`Task ${data.task_id?.slice(0, 8)} queued under ${data.agent}`, "info");
            } else if (data.type === "scheduler_changed") {
              refresh();
              showToast(`Active scheduler switched to ${data.scheduler}`, "info");
            } else if (data.type === "blocked_action") {
              refresh();
              showToast(`Policy boundary blocked action: ${data.tool || data.action}`, "error");
            }
          } catch {
            // Ignore malformed payloads
          }
        };

        ws.onclose = () => {
          reconnectTimer = setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch {
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState <= WebSocket.OPEN) ws.close();
    };
  }, [refresh]);

  // Switch scheduler
  const handleSwitchScheduler = async (newScheduler) => {
    try {
      const data = await api("/scheduler", {
        method: "POST",
        body: JSON.stringify({ scheduler: newScheduler }),
      });
      setScheduler(newScheduler);
      showToast(`Scheduler switched to ${data.scheduler}`, "success");
      await refresh();
    } catch (err) {
      showToast(`Scheduler switch failed: ${err.message}`, "error");
    }
  };

  return (
    <div className="agentos-app-shell">
      {/* Originkit Hyper Space Full-Screen Interactive Animated Background */}
      <div className="hyperspace-bg-container" aria-hidden="true">
        <Hyperspace
          background="#01020A"
          colors={["#0047FF", "#C7D2FE", "#000000"]}
          density={260}
          speed={18}
          perspective={78}
          streaks={{ length: 29, spread: 135, opacity: 100 }}
          tunnel={{ opacity: 100, roll: 90, glow: "#7464FFE6" }}
          pointer={{ steer: 200, boost: 135, damping: 100 }}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            minWidth: 0,
            minHeight: 0,
            zIndex: 0,
            pointerEvents: "none",
          }}
        />
      </div>

      {/* Background Ambient Holo-Glow Orbs */}
      <div className="holo-ambient holo-1" />
      <div className="holo-ambient holo-2" />
      <div className="holo-ambient holo-3" />
      <div className="scanline-overlay" />

      {/* Main Header & Nav */}
      <Header
        tab={tab}
        setTab={setTab}
        online={online}
        stats={stats}
        metrics={metrics}
        agentsCount={agents.length}
        queueCount={metrics?.queue_length || 0}
        blockedCount={blocked.length}
        figuresCount={figures.length}
        scheduler={scheduler}
        onSwitchScheduler={handleSwitchScheduler}
      />

      {/* Toast Notification */}
      {toast && (
        <div className={`cyber-toast toast-${toast.type}`}>
          <span className="toast-bullet" />
          <span>{toast.message}</span>
          <button className="toast-close" onClick={() => setToast(null)}>
            ×
          </button>
        </div>
      )}

      {/* Tab Workspaces */}
      <main className="workspace-container">
        {tab === "shell" && (
          <AiShellView
            api={api}
            metrics={metrics}
            stats={stats}
            agents={agents}
            scheduler={scheduler}
            onSwitchScheduler={handleSwitchScheduler}
            onTaskCompleted={refresh}
            events={events}
          />
        )}

        {tab === "scheduler" && (
          <SchedulerView
            scheduler={scheduler}
            onSwitchScheduler={handleSwitchScheduler}
            tasks={tasks}
            api={api}
            onRefresh={refresh}
            onInspectTask={setInspectingTask}
            metrics={metrics}
          />
        )}

        {tab === "agents" && <AgentsView agents={agents} api={api} />}

        {tab === "telemetry" && (
          <TelemetryView metrics={metrics} stats={stats} tasks={tasks} />
        )}

        {tab === "results" && (
          <ResultsView
            figures={figures}
            onRefreshFigures={refreshFigures}
            apiUrl={API_URL}
            api={api}
            tasks={tasks}
          />
        )}
      </main>

      {/* Task Inspection Modal */}
      {inspectingTask && (
        <TaskModal
          task={inspectingTask}
          onClose={() => setInspectingTask(null)}
        />
      )}

      {/* Cyberdeck System Footer */}
      <footer className="cyber-footer">
        <div className="footer-left">
          <span className="footer-mark">AGENTOS KERNEL LAYER</span>
          <span className="footer-sep">·</span>
          <span>LINUX/SYSTEM OS RUNTIME</span>
          <span className="footer-sep">·</span>
          <span>AUTONOMOUS MULTI-AGENT ENVIRONMENT</span>
        </div>
        <div className="footer-right">
          <span className="footer-status-dot" />
          <span>STATUS: <b>{online ? "SYNCHRONIZED" : "OFFLINE / RECONNECTING"}</b></span>
          <span className="footer-sep">·</span>
          <span>LOCAL ZERO-CDN STACK</span>
        </div>
      </footer>
    </div>
  );
}
