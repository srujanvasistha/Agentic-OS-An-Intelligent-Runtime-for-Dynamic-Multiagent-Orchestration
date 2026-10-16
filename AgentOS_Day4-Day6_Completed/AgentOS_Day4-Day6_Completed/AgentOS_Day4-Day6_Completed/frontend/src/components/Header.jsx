import {
  Terminal,
  Cpu,
  Bot,
  Activity,
  ShieldCheck,
  BarChart3,
  Volume2,
  VolumeX,
  Wifi,
  WifiOff,
  Layers,
  Sparkles,
} from "lucide-react";
import { isSoundEnabled, toggleSound, playCyberClick } from "../utils/audio";
import { useState } from "react";

export default function Header({
  tab,
  setTab,
  online,
  stats,
  metrics,
  agentsCount = 0,
  queueCount = 0,
  blockedCount = 0,
  figuresCount = 0,
  scheduler = "fifo",
  onSwitchScheduler,
}) {
  const [soundOn, setSoundOn] = useState(isSoundEnabled());

  const handleSoundToggle = () => {
    const next = toggleSound();
    setSoundOn(next);
    if (next) playCyberClick();
  };

  const handleTabClick = (t) => {
    playCyberClick();
    setTab(t);
  };

  const tabs = [
    { id: "shell", label: "AI Shell & Dispatcher", icon: Terminal, badge: null },
    { id: "scheduler", label: "Scheduler & Queue", icon: Cpu, badge: queueCount > 0 ? queueCount : null },
    { id: "agents", label: "Agent Fleet & Router", icon: Bot, badge: agentsCount },
    { id: "telemetry", label: "Telemetry & Charts", icon: Activity, badge: metrics ? `${Math.round(metrics.cpu_percent)}%` : null },
    { id: "results", label: "Benchmark Results", icon: BarChart3, badge: figuresCount || null },
  ];

  return (
    <header className="cyber-header">
      {/* Top Cyberdeck Status Strip */}
      <div className="header-top-row">
        <div className="brand-group">
          <div className="brand-badge-box">
            <span className="brand-hex">
              <Sparkles size={16} className="brand-icon-anim" />
            </span>
            <div className="brand-text">
              <div className="brand-title">
                AGENT<span className="brand-highlight">OS</span>
                <span className="os-version">v0.4.0</span>
              </div>
              <div className="brand-subtitle">
                AI-Native Operating Environment · Kernel System Layer
              </div>
            </div>
          </div>
        </div>

        {/* Global System Telemetry Badges */}
        <div className="header-badges">
          {/* Connection Status */}
          <div className={`sys-badge connection-badge ${online ? "online" : "offline"}`}>
            {online ? <Wifi size={13} /> : <WifiOff size={13} />}
            <span className="pulse-indicator" />
            <span>{online ? "SYSTEM ONLINE" : "DISCONNECTED"}</span>
          </div>

          {/* LLM Backend Badge */}
          <div className="sys-badge backend-badge">
            <span className="badge-tag">LLM BACKEND</span>
            <strong>{stats?.llm_backend?.toUpperCase() || "MOCK"}</strong>
            <span className="badge-sub">{stats?.model || "qwen2.5:1.5b"}</span>
          </div>

          {/* Active Scheduler Badge */}
          <div className="sys-badge scheduler-badge">
            <Layers size={13} />
            <span className="badge-tag">POLICY:</span>
            <select
              value={scheduler}
              onChange={(e) => onSwitchScheduler(e.target.value)}
              className="header-scheduler-select"
              title="Hot-swap scheduler policy"
            >
              <option value="fifo">FIFO</option>
              <option value="priority">Priority</option>
              <option value="roundrobin">Round Robin</option>
              <option value="resourceaware">Resource Aware</option>
            </select>
          </div>

          {/* Sound FX Button */}

          {/* Sound FX Button */}
          <button
            onClick={handleSoundToggle}
            className={`sound-toggle-btn ${soundOn ? "active" : ""}`}
            title={soundOn ? "Mute audio synthesis" : "Enable cybernetic sound effects"}
          >
            {soundOn ? <Volume2 size={14} /> : <VolumeX size={14} />}
          </button>
        </div>
      </div>

      {/* Cyber Navigation Tabs */}
      <nav className="cyber-nav-tabs">
        {tabs.map((item) => {
          const Icon = item.icon;
          const isActive = tab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleTabClick(item.id)}
              className={`cyber-tab ${isActive ? "active" : ""}`}
            >
              <Icon size={15} className="tab-icon" />
              <span className="tab-label">{item.label}</span>
              {item.badge !== null && (
                <span className={`tab-badge ${item.alert ? "badge-alert" : ""}`}>
                  {item.badge}
                </span>
              )}
              {isActive && <span className="tab-glow-line" />}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
