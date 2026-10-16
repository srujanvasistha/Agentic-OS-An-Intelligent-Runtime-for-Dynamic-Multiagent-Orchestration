import {
  Bot,
  FileCode,
  Shield,
  Compass,
  Wrench,
  Activity,
} from "lucide-react";

export default function AgentsView({ agents = [] }) {
  const getAgentDetails = (name) => {
    switch (name) {
      case "GeneralAgent":
        return {
          icon: Bot,
          color: "#00f0ff",
          border: "border-cyan",
          role: "General Reasoning & Execution",
          desc: "Handles multifaceted natural language requests, complex reasoning chains, decomposition, and default fallback tasks.",
          capabilities: ["general_reasoning", "task_execution", "orchestration", "synthesis"],
          tools: ["system_info"],
        };
      case "FileAgent":
        return {
          icon: FileCode,
          color: "#8b5cf6",
          border: "border-violet",
          role: "Workspace Filesystem Manager",
          desc: "Safely navigates, inspects, and interacts with workspace files within strict containment boundaries.",
          capabilities: ["file_inspection", "workspace_navigation", "text_extraction", "file_creation", "file_writing"],
          tools: ["filesystem"],
        };
      case "SecurityAgent":
        return {
          icon: Shield,
          color: "#f43f5e",
          border: "border-rose",
          role: "Policy Enforcement & Threat Guard",
          desc: "Verifies tool requests against default-deny policies, audits unauthorized commands, and monitors safety boundaries.",
          capabilities: ["policy_audit", "threat_detection", "default_deny_enforcement"],
          tools: ["system_info"],
        };
      case "MonitoringAgent":
        return {
          icon: Activity,
          color: "#f59e0b",
          border: "border-amber",
          role: "Telemetry & Anomaly Sentinel",
          desc: "Collects CPU, memory, queue, latency, and task-status information; detects operational anomalies and generates telemetry reports.",
          capabilities: ["monitoring", "system_metrics", "anomaly_detection", "operational_reports", "diagnostics"],
          tools: ["system_info"],
        };
      case "PlanningAgent":
        return {
          icon: Compass,
          color: "#10b981",
          border: "border-emerald",
          role: "Workflow Decomposition & Orchestrator",
          desc: "Breaks complex requests into subtasks, assigns them to suitable agents, tracks execution dependencies, and synthesizes combined outputs.",
          capabilities: ["task_planning", "subtask_decomposition", "dependency_tracking", "workflow_orchestration"],
          tools: [],
        };
      default:
        return {
          icon: Bot,
          color: "#06b6d4",
          border: "border-cyan",
          role: "Specialized Worker",
          desc: "Registered runtime agent.",
          capabilities: ["custom_execution"],
          tools: [],
        };
    }
  };

  return (
    <div className="agents-workspace">
      {/* Agent Fleet Cards */}
      <section className="agent-fleet-section">
        <div className="section-header-title">
          <Bot size={18} className="text-cyan" />
          <div>
            <h2>Registered Agent Fleet</h2>
            <p>Specialized autonomous workers coordinated by the AgentOS runtime router</p>
          </div>
        </div>

        <div className="agent-cards-grid">
          {agents.map((agent) => {
            const meta = getAgentDetails(agent.name);
            const Icon = meta.icon;
            return (
              <div
                key={agent.name}
                className="agent-hologram-card glass-panel"
                style={{ "--agent-accent": meta.color }}
              >
                <div className="agent-card-header">
                  <div className="agent-icon-box">
                    <Icon size={22} style={{ color: meta.color }} />
                  </div>
                  <div className="agent-title-info">
                    <h3>{agent.name}</h3>
                    <span className="agent-role-pill">{meta.role}</span>
                  </div>
                  <span className="agent-live-status">AVAILABLE</span>
                </div>

                <p className="agent-desc-text">{meta.desc}</p>

                {/* Model & Runtime spec */}
                <div className="agent-spec-box">
                  <span className="spec-label">MODEL BINDING</span>
                  <strong className="spec-val">{agent.model || "qwen2.5:1.5b"}</strong>
                </div>

                {/* Capabilities list */}
                <div className="capabilities-group">
                  <span className="group-label">CAPABILITIES</span>
                  <div className="caps-list">
                    {(agent.capabilities?.length ? agent.capabilities : meta.capabilities).map(
                      (cap, idx) => (
                        <span key={idx} className="cap-tag">
                          {cap}
                        </span>
                      )
                    )}
                  </div>
                </div>

                {/* Allowed Tools */}
                <div className="tools-group">
                  <span className="group-label">ALLOWED TOOLS</span>
                  <div className="tools-list">
                    {(agent.allowed_tools?.length ? agent.allowed_tools : meta.tools).map(
                      (tool, idx) => (
                        <span key={idx} className="tool-tag">
                          <Wrench size={11} /> {tool}
                        </span>
                      )
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
