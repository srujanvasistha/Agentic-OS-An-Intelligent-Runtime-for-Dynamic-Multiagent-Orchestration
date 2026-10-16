import { X, Copy, Check, Clock, Cpu, Award, ShieldAlert, FileText } from "lucide-react";
import { useState } from "react";

export default function TaskModal({ task, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!task) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(task, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "done":
        return "text-emerald";
      case "running":
        return "text-cyan";
      case "queued":
        return "text-amber";
      case "failed":
      case "blocked":
        return "text-rose";
      default:
        return "text-slate";
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-window glass-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-eyebrow">TASK INSPECTOR</span>
            <h3>{task.id}</h3>
          </div>
          <div className="modal-header-actions">
            <button className="icon-btn" onClick={handleCopy} title="Copy task JSON">
              {copied ? <Check size={16} className="text-emerald" /> : <Copy size={16} />}
            </button>
            <button className="icon-btn" onClick={onClose} title="Close modal">
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          {/* Quick Stats Grid */}
          <div className="modal-stats-grid">
            <div className="modal-stat-box">
              <span className="stat-label">STATUS</span>
              <strong className={`stat-value ${getStatusColor(task.status)}`}>
                {task.status?.toUpperCase()}
              </strong>
            </div>
            <div className="modal-stat-box">
              <span className="stat-label">AGENT TYPE</span>
              <strong className="stat-value text-cyan">{task.agent_type || task.agent || "Auto"}</strong>
            </div>
            <div className="modal-stat-box">
              <span className="stat-label">PRIORITY</span>
              <strong className="stat-value text-amber">{task.priority ?? 5} / 10</strong>
            </div>
            <div className="modal-stat-box">
              <span className="stat-label">EST. TOKENS</span>
              <strong className="stat-value">{task.estimated_tokens || 256}</strong>
            </div>
          </div>

          {/* Prompt Section */}
          <div className="modal-section">
            <div className="section-label">
              <FileText size={13} />
              <span>SUBMITTED PROMPT</span>
            </div>
            <div className="modal-prompt-box">{task.prompt}</div>
          </div>

          {/* Response / Output Section */}
          {(task.response || task.result) && (
            <div className="modal-section">
              <div className="section-label">
                <Cpu size={13} />
                <span>EXECUTION RESPONSE</span>
              </div>
              <pre className="modal-response-box">
                {task.response ||
                  (task.result?.response
                    ? task.result.response
                    : JSON.stringify(task.result, null, 2))}
              </pre>
            </div>
          )}

          {/* Timestamps & Capabilities */}
          <div className="modal-meta-grid">
            <div>
              <span className="stat-label">SUBMITTED AT</span>
              <div>{task.submitted_at ? new Date(task.submitted_at).toLocaleString() : "—"}</div>
            </div>
            <div>
              <span className="stat-label">STARTED AT</span>
              <div>{task.started_at ? new Date(task.started_at).toLocaleString() : "—"}</div>
            </div>
            <div>
              <span className="stat-label">COMPLETED AT</span>
              <div>{task.completed_at ? new Date(task.completed_at).toLocaleString() : "—"}</div>
            </div>
            <div>
              <span className="stat-label">LATENCY</span>
              <div>
                {task.latency_seconds ? `${Number(task.latency_seconds).toFixed(2)}s` : "—"}
              </div>
            </div>
          </div>

          {/* Raw JSON Accordion */}
          <details className="modal-raw-details">
            <summary>View Raw JSON Payload</summary>
            <pre className="code-view">{JSON.stringify(task, null, 2)}</pre>
          </details>
        </div>
      </div>
    </div>
  );
}
