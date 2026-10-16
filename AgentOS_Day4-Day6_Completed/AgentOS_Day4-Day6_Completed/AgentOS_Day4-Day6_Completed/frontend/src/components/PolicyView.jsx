import { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Search,
  AlertTriangle,
  Clock,
  Terminal,
  FileX,
  ExternalLink,
} from "lucide-react";

export default function PolicyView({ blocked = [], api }) {
  const [search, setSearch] = useState("");

  const filteredBlocked = blocked.filter((b) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      b.action?.toLowerCase().includes(q) ||
      b.tool?.toLowerCase().includes(q) ||
      b.reason?.toLowerCase().includes(q) ||
      b.agent?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="policy-workspace">
      {/* Policy Security Header Card */}
      <section className="policy-banner glass-panel">
        <div className="policy-banner-left">
          <div className="shield-symbol-box">
            <ShieldCheck size={36} className="text-emerald" />
          </div>
          <div>
            <h2>Default-Deny Policy Enforcement Guard</h2>
            <p>
              AgentOS implements an application-layer default-deny tool boundary. Any tool
              invocation, shell command, or filesystem path not explicitly whitelisted is intercepted
              and audited.
            </p>
          </div>
        </div>

        <div className="policy-metrics-pill-group">
          <div className="policy-pill">
            <span className="pill-title">AUDITED DENIALS</span>
            <strong className="text-rose">{blocked.length}</strong>
          </div>
          <div className="policy-pill">
            <span className="pill-title">ENFORCEMENT MODE</span>
            <strong className="text-emerald">ACTIVE</strong>
          </div>
        </div>
      </section>

      {/* Security Principles Cards */}
      <section className="security-rules-grid">
        <div className="rule-card glass-panel">
          <div className="rule-top">
            <Lock size={16} className="text-cyan" />
            <h4>Sandbox Tool Isolation</h4>
          </div>
          <p>
            Agents are prevented from spawning arbitrary subshells, executing bash binaries, or
            invoking system utilities unless exposed via the ToolRegistry interface.
          </p>
        </div>

        <div className="rule-card glass-panel">
          <div className="rule-top">
            <FileX size={16} className="text-violet" />
            <h4>Path Traversal Protection</h4>
          </div>
          <p>
            FileSystemTool validates target filepaths against the designated workspace boundary,
            blocking directory escapes (`../`) and unauthorized root access.
          </p>
        </div>

        <div className="rule-card glass-panel">
          <div className="rule-top">
            <Terminal size={16} className="text-amber" />
            <h4>Zero Arbitrary Execution</h4>
          </div>
          <p>
            Incoming user prompts and agent responses are strictly handled as structured AI tasks.
            The web console never runs raw bash or PowerShell commands on the host.
          </p>
        </div>
      </section>

      {/* Blocked Actions Audit Log */}
      <section className="audit-log-section glass-panel">
        <div className="audit-header-row">
          <div className="title-with-icon">
            <ShieldAlert size={16} className="text-rose" />
            <div>
              <h3>Security Audit Log (GET /blocked)</h3>
              <p>Chronological audit record of intercepted actions and policy denial rationales</p>
            </div>
          </div>

          <div className="audit-search-box">
            <Search size={14} className="text-slate" />
            <input
              type="text"
              placeholder="Filter audit logs by action or reason..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="audit-items-list">
          {filteredBlocked.length === 0 ? (
            <div className="empty-audit-state">
              <ShieldCheck size={32} className="text-emerald" />
              <h4>No blocked actions found</h4>
              <p>
                {blocked.length === 0
                  ? "No unauthorized actions have been attempted during this runtime session."
                  : "No audit records match your search filter."}
              </p>
            </div>
          ) : (
            filteredBlocked.map((item, idx) => (
              <div key={idx} className="audit-record-card">
                <div className="audit-record-top">
                  <div className="audit-action-title">
                    <AlertTriangle size={15} className="text-rose" />
                    <strong>{item.action || item.tool || "Unauthorized Action"}</strong>
                    <span className="badge-pill bg-rose">DENIED</span>
                  </div>
                  <span className="audit-timestamp">
                    <Clock size={12} />
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Recently"}
                  </span>
                </div>

                <div className="audit-reason-box">
                  <span className="reason-label">POLICY RATIONALE:</span>
                  <p>{item.reason || "Violated default-deny tool boundary constraint."}</p>
                </div>

                <div className="audit-meta-row">
                  <span>
                    TARGET AGENT: <b>{item.agent || "Unknown Agent"}</b>
                  </span>
                  <span>
                    BOUNDARY: <b>Application Layer Default-Deny</b>
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
