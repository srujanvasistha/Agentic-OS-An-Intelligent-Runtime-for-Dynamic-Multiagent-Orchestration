import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Cpu,
  HardDrive,
  Clock,
  Zap,
  TrendingUp,
  BarChart2,
  Copy,
  Check,
  Server,
  Layers,
} from "lucide-react";

export default function TelemetryView({ metrics, stats, tasks = [] }) {
  const cpuCanvasRef = useRef(null);
  const ramCanvasRef = useRef(null);
  const [copiedRaw, setCopiedRaw] = useState(false);

  // History buffers for real-time charts (30 data points)
  const cpuHistoryRef = useRef(Array(30).fill(metrics?.cpu_percent || 15));
  const ramHistoryRef = useRef(Array(30).fill(metrics?.ram_percent || 40));

  // Push new samples when metrics update
  useEffect(() => {
    if (!metrics) return;
    cpuHistoryRef.current.push(metrics.cpu_percent || 0);
    if (cpuHistoryRef.current.length > 30) cpuHistoryRef.current.shift();

    ramHistoryRef.current.push(metrics.ram_percent || 0);
    if (ramHistoryRef.current.length > 30) ramHistoryRef.current.shift();
  }, [metrics]);

  // Render CPU Chart on Canvas
  useEffect(() => {
    const canvas = cpuCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = (canvas.width = canvas.parentElement.clientWidth || 400);
    const height = (canvas.height = 140);

    ctx.clearRect(0, 0, width, height);

    const data = cpuHistoryRef.current;
    const step = width / (data.length - 1);

    // Draw Grid Lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((pct) => {
      ctx.beginPath();
      ctx.moveTo(0, height * pct);
      ctx.lineTo(width, height * pct);
      ctx.stroke();
    });

    // Draw Gradient Area
    ctx.beginPath();
    ctx.moveTo(0, height);
    data.forEach((val, i) => {
      const y = height - (val / 100) * (height - 20) - 10;
      ctx.lineTo(i * step, y);
    });
    ctx.lineTo(width, height);
    ctx.closePath();

    const areaGrad = ctx.createLinearGradient(0, 0, 0, height);
    areaGrad.addColorStop(0, "rgba(0, 240, 255, 0.35)");
    areaGrad.addColorStop(1, "rgba(0, 240, 255, 0.0)");
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Draw Line
    ctx.beginPath();
    data.forEach((val, i) => {
      const y = height - (val / 100) * (height - 20) - 10;
      if (i === 0) ctx.moveTo(0, y);
      else ctx.lineTo(i * step, y);
    });
    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Latest point glow
    const lastX = width;
    const lastY = height - (data[data.length - 1] / 100) * (height - 20) - 10;
    ctx.beginPath();
    ctx.arc(lastX - 2, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.shadowColor = "#00f0ff";
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  }, [metrics]);

  // Render RAM Chart on Canvas
  useEffect(() => {
    const canvas = ramCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = (canvas.width = canvas.parentElement.clientWidth || 400);
    const height = (canvas.height = 140);

    ctx.clearRect(0, 0, width, height);

    const data = ramHistoryRef.current;
    const step = width / (data.length - 1);

    // Draw Grid Lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((pct) => {
      ctx.beginPath();
      ctx.moveTo(0, height * pct);
      ctx.lineTo(width, height * pct);
      ctx.stroke();
    });

    // Draw Gradient Area
    ctx.beginPath();
    ctx.moveTo(0, height);
    data.forEach((val, i) => {
      const y = height - (val / 100) * (height - 20) - 10;
      ctx.lineTo(i * step, y);
    });
    ctx.lineTo(width, height);
    ctx.closePath();

    const areaGrad = ctx.createLinearGradient(0, 0, 0, height);
    areaGrad.addColorStop(0, "rgba(139, 92, 246, 0.35)");
    areaGrad.addColorStop(1, "rgba(139, 92, 246, 0.0)");
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Draw Line
    ctx.beginPath();
    data.forEach((val, i) => {
      const y = height - (val / 100) * (height - 20) - 10;
      if (i === 0) ctx.moveTo(0, y);
      else ctx.lineTo(i * step, y);
    });
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Latest point glow
    const lastX = width;
    const lastY = height - (data[data.length - 1] / 100) * (height - 20) - 10;
    ctx.beginPath();
    ctx.arc(lastX - 2, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.shadowColor = "#8b5cf6";
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  }, [metrics]);

  const copyRawJson = () => {
    navigator.clipboard.writeText(JSON.stringify(metrics, null, 2));
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  // Task distribution calculations
  const total = tasks.length || 1;
  const done = tasks.filter((t) => t.status === "done").length;
  const queued = tasks.filter((t) => t.status === "queued").length;
  const failed = tasks.filter((t) => t.status === "failed" || t.status === "blocked").length;

  return (
    <div className="telemetry-workspace">
      {/* Real-time Moving Graphs Row */}
      <section className="telemetry-charts-grid">
        {/* CPU Chart */}
        <div className="chart-card glass-panel">
          <div className="chart-header">
            <div className="chart-title-group">
              <Cpu size={16} className="text-cyan" />
              <div>
                <h4>CPU Utilization Over Time</h4>
                <span>Real-time rolling sample buffer (last 30 seconds)</span>
              </div>
            </div>
            <div className="current-stat-badge">
              <strong className="text-cyan">{metrics ? `${metrics.cpu_percent.toFixed(1)}%` : "—"}</strong>
            </div>
          </div>
          <div className="chart-canvas-box">
            <canvas ref={cpuCanvasRef} />
          </div>
        </div>

        {/* RAM Chart */}
        <div className="chart-card glass-panel">
          <div className="chart-header">
            <div className="chart-title-group">
              <HardDrive size={16} className="text-violet" />
              <div>
                <h4>Virtual Memory Load Over Time</h4>
                <span>Host RAM allocation percentage</span>
              </div>
            </div>
            <div className="current-stat-badge">
              <strong className="text-violet">{metrics ? `${metrics.ram_percent.toFixed(1)}%` : "—"}</strong>
            </div>
          </div>
          <div className="chart-canvas-box">
            <canvas ref={ramCanvasRef} />
          </div>
        </div>
      </section>

      {/* Hardware Gauge Cards Grid */}
      <section className="hardware-gauges-grid">
        <div className="gauge-card glass-panel">
          <div className="gauge-top">
            <span className="gauge-title">PHYSICAL RAM CONSUMPTION</span>
            <HardDrive size={14} className="text-violet" />
          </div>
          <div className="gauge-metric-value">
            {metrics ? `${metrics.ram_used_mb} MB` : "—"}
          </div>
          <div className="gauge-sub">
            Total capacity: {metrics ? `${metrics.ram_total_mb} MB` : "—"}
          </div>
          <div className="gauge-bar-track">
            <div
              className="gauge-bar-fill bg-violet-grad"
              style={{ width: `${Math.min(100, metrics?.ram_percent || 0)}%` }}
            />
          </div>
        </div>

        <div className="gauge-card glass-panel">
          <div className="gauge-top">
            <span className="gauge-title">COMPLETED TASK LATENCY</span>
            <Clock size={14} className="text-cyan" />
          </div>
          <div className="gauge-metric-value text-cyan">
            {metrics?.latency_seconds ? `${Number(metrics.latency_seconds).toFixed(2)}s` : "0.00s"}
          </div>
          <div className="gauge-sub">Mean completed task duration</div>
          <div className="gauge-bar-track">
            <div
              className="gauge-bar-fill bg-cyan-grad"
              style={{ width: `${Math.min(100, (metrics?.latency_seconds || 0) * 8)}%` }}
            />
          </div>
        </div>

        <div className="gauge-card glass-panel">
          <div className="gauge-top">
            <span className="gauge-title">TOTAL TOKENS GENERATED</span>
            <Zap size={14} className="text-emerald" />
          </div>
          <div className="gauge-metric-value text-emerald">
            {(metrics?.tokens_total ?? 0).toLocaleString()}
          </div>
          <div className="gauge-sub">Recorded across all scheduler runs</div>
          <div className="gauge-bar-track">
            <div className="gauge-bar-fill bg-emerald-grad" style={{ width: "100%" }} />
          </div>
        </div>

        <div className="gauge-card glass-panel">
          <div className="gauge-top">
            <span className="gauge-title">PERSISTED TASKS</span>
            <Server size={14} className="text-amber" />
          </div>
          <div className="gauge-metric-value text-amber">
            {metrics?.tasks_total ?? tasks.length}
          </div>
          <div className="gauge-sub">Stored in SQLite backend database</div>
          <div className="gauge-bar-track">
            <div className="gauge-bar-fill bg-amber-grad" style={{ width: "100%" }} />
          </div>
        </div>
      </section>

      {/* Task Status Distribution Bar */}
      <section className="distribution-section glass-panel">
        <div className="section-header-title">
          <BarChart2 size={16} className="text-cyan" />
          <div>
            <h3>Task Outcome Distribution</h3>
            <p>Proportion of completed, queued, and denied/failed tasks in current runtime store</p>
          </div>
        </div>

        {/* Multi-segment Progress Bar */}
        <div className="distribution-bar-track">
          <div
            className="bar-seg seg-done"
            style={{ width: `${(done / total) * 100}%` }}
            title={`Completed: ${done}`}
          />
          <div
            className="bar-seg seg-queued"
            style={{ width: `${(queued / total) * 100}%` }}
            title={`Queued: ${queued}`}
          />
          <div
            className="bar-seg seg-failed"
            style={{ width: `${(failed / total) * 100}%` }}
            title={`Failed/Blocked: ${failed}`}
          />
        </div>

        <div className="distribution-legend">
          <div className="legend-item">
            <span className="dot dot-done" />
            <span>Done ({done})</span>
          </div>
          <div className="legend-item">
            <span className="dot dot-queued" />
            <span>Queued ({queued})</span>
          </div>
          <div className="legend-item">
            <span className="dot dot-failed" />
            <span>Failed / Denied ({failed})</span>
          </div>
        </div>
      </section>

      {/* Raw JSON Telemetry Snapshot */}
      <section className="raw-telemetry-section glass-panel">
        <div className="raw-header">
          <div>
            <h4>Host Telemetry Snapshot (GET /metrics)</h4>
            <span>Unprocessed system diagnostic response</span>
          </div>
          <button className="icon-btn-sm" onClick={copyRawJson} title="Copy JSON">
            {copiedRaw ? <Check size={13} className="text-emerald" /> : <Copy size={13} />}
          </button>
        </div>
        <pre className="code-view">{JSON.stringify(metrics || {}, null, 2)}</pre>
      </section>
    </div>
  );
}
