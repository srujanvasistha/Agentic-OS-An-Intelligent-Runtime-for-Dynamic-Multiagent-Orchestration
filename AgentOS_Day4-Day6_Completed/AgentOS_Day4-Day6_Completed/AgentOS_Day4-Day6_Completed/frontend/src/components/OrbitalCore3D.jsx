import { useEffect, useRef } from "react";

/**
 * Helper to convert hex colors to RGBA string
 */
function hexToRgba(hex, alpha = 1) {
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Draw a smooth rounded rectangle
 */
function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

const FIXED_HEIGHT = 260; // Strict fixed initial height prevents any unbounded expansion

/**
 * Interactive 3D Canvas Visualizer for AgentOS Core & Dispatcher
 * Renders rotating 3D orbital rings, scheduler policy core, and agent balls.
 * When agents are running, the ball becomes significantly bigger, pulses with
 * multi-tier neon glows, expanding radar shockwaves, energy halos, and laser links.
 * Height is strictly clamped to initial 260px so the container never expands.
 */
export default function OrbitalCore3D({
  agents = [],
  activeAgent = null,
  isProcessing = false,
  metrics = null,
  scheduler = "fifo",
  onSelectAgent = null,
}) {
  const canvasRef = useRef(null);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0, canvasX: -999, canvasY: -999 });
  const renderedAgentsRef = useRef([]);

  // Store dynamic props in refs so animation loop uses latest state without re-mounting canvas
  const activeAgentRef = useRef(activeAgent);
  activeAgentRef.current = activeAgent;
  const isProcessingRef = useRef(isProcessing);
  isProcessingRef.current = isProcessing;
  const metricsRef = useRef(metrics);
  metricsRef.current = metrics;
  const schedulerRef = useRef(scheduler);
  schedulerRef.current = scheduler;
  const onSelectAgentRef = useRef(onSelectAgent);
  onSelectAgentRef.current = onSelectAgent;

  const agentList = [
    { name: "GeneralAgent", label: "GEN", title: "General Reasoner", color: "#00f0ff", angle: 0 },
    { name: "FileAgent", label: "FILE", title: "Filesystem Ops", color: "#a855f7", angle: (2 * Math.PI * 1) / 5 },
    { name: "SecurityAgent", label: "SEC", title: "Policy & Threat Guard", color: "#f43f5e", angle: (2 * Math.PI * 2) / 5 },
    { name: "MonitoringAgent", label: "MON", title: "Telemetry & Logs", color: "#f59e0b", angle: (2 * Math.PI * 3) / 5 },
    { name: "PlanningAgent", label: "PLAN", title: "Subtask Decomposition", color: "#10b981", angle: (2 * Math.PI * 4) / 5 },
  ];

  const isAgentActive = (agent, currentActiveAgent, currentProcessing) => {
    if (currentActiveAgent) {
      const q = String(currentActiveAgent).toLowerCase().trim();
      const aName = agent.name.toLowerCase();
      const aLabel = agent.label.toLowerCase();
      const aStem = aName.replace("agent", "");
      return (
        q === aName ||
        q === aLabel ||
        q === aStem ||
        q.includes(aStem) ||
        aName.includes(q) ||
        q.includes(aLabel)
      );
    }
    if (currentProcessing) {
      return agent.name === "GeneralAgent";
    }
    return false;
  };

  const currentRunningAgent = agentList.find((ag) => isAgentActive(ag, activeAgent, isProcessing));
  const anyRunning = Boolean(currentRunningAgent || isProcessing);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animId;

    // Set fixed initial dimensions; height is permanently clamped to FIXED_HEIGHT (260)
    let width = (canvas.width = canvas.parentElement ? canvas.parentElement.clientWidth : 640);
    let height = (canvas.height = FIXED_HEIGHT);

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth || 640;
      height = canvas.height = FIXED_HEIGHT;
    };
    window.addEventListener("resize", handleResize);

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      mouseRef.current.canvasX = clientX;
      mouseRef.current.canvasY = clientY;
      mouseRef.current.targetX = (clientX / width - 0.5) * 2;
      mouseRef.current.targetY = (clientY / height - 0.5) * 2;

      let hovered = false;
      for (const ag of renderedAgentsRef.current) {
        const dist = Math.hypot(clientX - ag.x, clientY - ag.y);
        if (dist <= Math.max(ag.radius + 8, 24)) {
          hovered = true;
          break;
        }
      }
      canvas.style.cursor = hovered ? "pointer" : "default";
    };
    canvas.addEventListener("mousemove", handleMouseMove);

    const handleMouseLeave = () => {
      mouseRef.current.targetX = 0;
      mouseRef.current.targetY = 0;
      mouseRef.current.canvasX = -999;
      mouseRef.current.canvasY = -999;
      canvas.style.cursor = "default";
    };
    canvas.addEventListener("mouseleave", handleMouseLeave);

    const handleClick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      for (const ag of renderedAgentsRef.current) {
        const dist = Math.hypot(clickX - ag.x, clickY - ag.y);
        if (dist <= Math.max(ag.radius + 10, 26)) {
          if (onSelectAgentRef.current) {
            onSelectAgentRef.current(ag.name);
          }
          return;
        }
      }
    };
    canvas.addEventListener("click", handleClick);

    // 3D background particle dust
    const particleCount = 75;
    const particles = Array.from({ length: particleCount }, () => ({
      x: (Math.random() - 0.5) * 440,
      y: (Math.random() - 0.5) * 260,
      z: (Math.random() - 0.5) * 440,
      radius: Math.random() * 1.6 + 0.6,
      alpha: Math.random() * 0.7 + 0.25,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      vz: (Math.random() - 0.5) * 0.45,
    }));

    const packets = [];
    let packetTimer = 0;
    let rotX = 0.32;
    let rotY = 0;
    let rotZ = 0;

    const project = (x, y, z, cx, cy) => {
      const fov = 350;
      const distance = z + 430;
      if (distance <= 1) return { x: cx, y: cy, scale: 0, visible: false };
      const scale = fov / distance;
      return {
        x: cx + x * scale,
        y: cy + y * scale,
        scale,
        visible: distance > 20,
      };
    };

    const rotatePoint = (x, y, z, rx, ry, rz) => {
      let cos = Math.cos(ry);
      let sin = Math.sin(ry);
      let x1 = x * cos + z * sin;
      let y1 = y;
      let z1 = -x * sin + z * cos;

      cos = Math.cos(rx);
      sin = Math.sin(rx);
      let x2 = x1;
      let y2 = y1 * cos - z1 * sin;
      let z2 = y1 * sin + z1 * cos;

      cos = Math.cos(rz);
      sin = Math.sin(rz);
      let x3 = x2 * cos - y2 * sin;
      let y3 = x2 * sin + y2 * cos;
      let z3 = z2;

      return { x: x3, y: y3, z: z3 };
    };

    let lastTime = performance.now();

    const render = (now) => {
      const dt = Math.min(50, now - lastTime) / 1000;
      lastTime = now;

      const currentActiveAgent = activeAgentRef.current;
      const currentProcessing = isProcessingRef.current;
      const currentMetrics = metricsRef.current;
      const currentScheduler = schedulerRef.current;
      const isAnyRunning = Boolean(currentActiveAgent || currentProcessing);

      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.08;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.08;

      const speedMult = isAnyRunning ? 1.7 : 1.0;
      const cpuLoad = currentMetrics?.cpu_percent || 15;
      const loadSpeed = 0.45 + (cpuLoad / 100) * 0.55;

      rotY += 0.32 * speedMult * loadSpeed * dt;
      rotX = 0.28 + mouseRef.current.y * 0.35;
      rotZ = mouseRef.current.x * 0.25;

      ctx.clearRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;

      // Background ambient space glow
      const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, Math.max(width, height) * 0.65);
      grad.addColorStop(0, isAnyRunning ? "rgba(0, 240, 255, 0.14)" : "rgba(0, 240, 255, 0.04)");
      grad.addColorStop(0.5, isAnyRunning ? "rgba(168, 85, 247, 0.05)" : "rgba(168, 85, 247, 0.02)");
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Render floating 3D particle dust
      ctx.fillStyle = "#00f0ff";
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;
        if (p.x > 220) p.x = -220;
        if (p.x < -220) p.x = 220;
        if (p.y > 130) p.y = -130;
        if (p.y < -130) p.y = 130;
        if (p.z > 220) p.z = -220;
        if (p.z < -220) p.z = 220;

        const rotated = rotatePoint(p.x, p.y, p.z, rotX * 0.5, rotY * 0.5, rotZ * 0.5);
        const pt = project(rotated.x, rotated.y, rotated.z, cx, cy);
        if (pt.visible) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, Math.max(0.5, p.radius * pt.scale), 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0, 240, 255, ${p.alpha * Math.min(1, pt.scale)})`;
          ctx.fill();
        }
      });

      // 3D Orbital Rings
      const rings = [
        { radius: 130, rx: rotX, ry: rotY, rz: rotZ, color: isAnyRunning ? "rgba(0, 240, 255, 0.45)" : "rgba(0, 240, 255, 0.28)", width: isAnyRunning ? 1.8 : 1.2 },
        { radius: 165, rx: rotX + 0.38, ry: -rotY * 0.7, rz: rotZ - 0.2, color: "rgba(168, 85, 247, 0.22)", width: 1.0 },
        { radius: 92, rx: rotX - 0.28, ry: rotY * 1.25, rz: rotZ + 0.25, color: "rgba(16, 185, 129, 0.25)", width: 1.0 },
      ];

      rings.forEach((ring) => {
        const segments = 48;
        ctx.beginPath();
        let first = true;
        for (let i = 0; i <= segments; i++) {
          const theta = (i / segments) * Math.PI * 2;
          const rx = Math.cos(theta) * ring.radius;
          const rz = Math.sin(theta) * ring.radius;
          const rotated = rotatePoint(rx, 0, rz, ring.rx, ring.ry, ring.rz);
          const pt = project(rotated.x, rotated.y, rotated.z, cx, cy);
          if (pt.visible) {
            if (first) {
              ctx.moveTo(pt.x, pt.y);
              first = false;
            } else {
              ctx.lineTo(pt.x, pt.y);
            }
          }
        }
        ctx.strokeStyle = ring.color;
        ctx.lineWidth = ring.width;
        ctx.stroke();
      });

      // Calculate 3D positions of agent nodes on primary orbit
      const orbitRadius = 130;
      const projectedAgents = agentList.map((agent) => {
        const theta = agent.angle + rotY;
        const x = Math.cos(theta) * orbitRadius;
        const z = Math.sin(theta) * orbitRadius;
        const y = Math.sin(theta * 2 + now * 0.0025) * 14;
        const rotated = rotatePoint(x, y, z, rotX, 0, rotZ);
        const pt = project(rotated.x, rotated.y, rotated.z, cx, cy);
        const running = isAgentActive(agent, currentActiveAgent, currentProcessing);
        return {
          ...agent,
          pt,
          z3d: rotated.z,
          isRunning: running,
        };
      });

      // Center Core (Scheduler Core)
      const coreRot = rotatePoint(0, 0, 0, rotX, rotY, rotZ);
      const corePt = project(coreRot.x, coreRot.y, coreRot.z, cx, cy);

      // Lines connecting scheduler core to each agent node
      projectedAgents.forEach((agent) => {
        if (!agent.pt.visible || !corePt.visible) return;

        if (agent.isRunning) {
          ctx.beginPath();
          ctx.moveTo(corePt.x, corePt.y);
          ctx.lineTo(agent.pt.x, agent.pt.y);
          ctx.strokeStyle = hexToRgba(agent.color, 0.7);
          ctx.lineWidth = 6 * agent.pt.scale;
          ctx.shadowColor = agent.color;
          ctx.shadowBlur = 18;
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(corePt.x, corePt.y);
          ctx.lineTo(agent.pt.x, agent.pt.y);
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2 * agent.pt.scale;
          ctx.shadowBlur = 8;
          ctx.stroke();
          ctx.shadowBlur = 0;
        } else {
          ctx.beginPath();
          ctx.moveTo(corePt.x, corePt.y);
          ctx.lineTo(agent.pt.x, agent.pt.y);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      });

      // Data packets along beam
      packetTimer += dt;
      const packetInterval = isAnyRunning ? 0.12 : 0.45;
      if (packetTimer > packetInterval) {
        packetTimer = 0;
        const target = projectedAgents.find((a) => a.isRunning) || projectedAgents[Math.floor(Math.random() * projectedAgents.length)];
        packets.push({
          progress: 0,
          targetAgent: target,
          color: target.color,
          speed: isAnyRunning ? 2.6 : 1.4,
          size: target.isRunning ? 5.5 : 3.0,
        });
      }

      for (let i = packets.length - 1; i >= 0; i--) {
        const pkt = packets[i];
        pkt.progress += pkt.speed * dt;
        if (pkt.progress >= 1) {
          packets.splice(i, 1);
          continue;
        }
        if (corePt.visible && pkt.targetAgent.pt.visible) {
          const px = corePt.x + (pkt.targetAgent.pt.x - corePt.x) * pkt.progress;
          const py = corePt.y + (pkt.targetAgent.pt.y - corePt.y) * pkt.progress;
          ctx.beginPath();
          ctx.arc(px, py, pkt.size, 0, Math.PI * 2);
          ctx.fillStyle = "#ffffff";
          ctx.shadowColor = pkt.color;
          ctx.shadowBlur = 14;
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }

      // Render Central Scheduler Core Sphere
      if (corePt.visible) {
        const schedulerPulsing = isAnyRunning ? Math.sin(now * 0.005) * 3 : 0;
        const baseCoreRadius = isAnyRunning ? 28 : 18;
        const coreRadius = (baseCoreRadius + schedulerPulsing) * corePt.scale;

        if (isAnyRunning) {
          const coreHalo = ctx.createRadialGradient(corePt.x, corePt.y, coreRadius * 0.8, corePt.x, corePt.y, coreRadius * 2.2);
          coreHalo.addColorStop(0, "rgba(0, 240, 255, 0.45)");
          coreHalo.addColorStop(1, "rgba(0, 240, 255, 0)");
          ctx.beginPath();
          ctx.arc(corePt.x, corePt.y, coreRadius * 2.2, 0, Math.PI * 2);
          ctx.fillStyle = coreHalo;
          ctx.fill();
        }

        const coreGrad = ctx.createRadialGradient(
          corePt.x - coreRadius * 0.35,
          corePt.y - coreRadius * 0.35,
          coreRadius * 0.1,
          corePt.x,
          corePt.y,
          coreRadius
        );
        coreGrad.addColorStop(0, "#ffffff");
        coreGrad.addColorStop(0.3, isAnyRunning ? "#00f0ff" : "#38bdf8");
        coreGrad.addColorStop(0.75, isAnyRunning ? "#0284c7" : "#0f172a");
        coreGrad.addColorStop(1, "#020617");

        ctx.beginPath();
        ctx.arc(corePt.x, corePt.y, coreRadius, 0, Math.PI * 2);
        ctx.fillStyle = coreGrad;
        ctx.shadowColor = isAnyRunning ? "#00f0ff" : "rgba(0, 240, 255, 0.4)";
        ctx.shadowBlur = isAnyRunning ? 32 : 12;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.strokeStyle = isAnyRunning ? "rgba(255, 255, 255, 0.85)" : "rgba(255, 255, 255, 0.45)";
        ctx.lineWidth = isAnyRunning ? 2 : 1;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = `bold ${Math.round((isAnyRunning ? 10 : 8) * corePt.scale)}px monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(currentScheduler.toUpperCase().slice(0, 4), corePt.x, corePt.y);
      }

      // Sort agent nodes by depth before drawing
      const sortedAgents = [...projectedAgents].sort((a, b) => a.z3d - b.z3d);
      const currentRenderedPointers = [];

      sortedAgents.forEach((agent) => {
        if (!agent.pt.visible) return;

        const isRunning = agent.isRunning;
        const pulse = isRunning ? Math.sin(now * 0.007) * 3.5 : 0;
        const baseRadius = isRunning ? 34 : 13.5;
        const nodeRadius = (baseRadius + pulse) * agent.pt.scale;

        currentRenderedPointers.push({
          name: agent.name,
          x: agent.pt.x,
          y: agent.pt.y,
          radius: nodeRadius,
          isRunning,
        });

        if (isRunning) {
          // Large radiant flare behind ball
          const flareRadius = nodeRadius * 2.8;
          const flareGrad = ctx.createRadialGradient(
            agent.pt.x,
            agent.pt.y,
            nodeRadius * 0.4,
            agent.pt.x,
            agent.pt.y,
            flareRadius
          );
          flareGrad.addColorStop(0, hexToRgba(agent.color, 0.5));
          flareGrad.addColorStop(0.5, hexToRgba(agent.color, 0.2));
          flareGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, flareRadius, 0, Math.PI * 2);
          ctx.fillStyle = flareGrad;
          ctx.fill();

          // Triple expanding radar shockwave rings
          for (let r = 0; r < 3; r++) {
            const waveProgress = ((now * 0.0013 + r * 0.33) % 1);
            const waveRadius = nodeRadius + waveProgress * 36 * agent.pt.scale;
            const waveAlpha = (1 - waveProgress) * 0.85;
            ctx.beginPath();
            ctx.arc(agent.pt.x, agent.pt.y, waveRadius, 0, Math.PI * 2);
            ctx.strokeStyle = hexToRgba(agent.color, waveAlpha);
            ctx.lineWidth = Math.max(1.2, (1 - waveProgress) * 3);
            ctx.stroke();
          }

          // Rotating energy ring
          ctx.save();
          ctx.translate(agent.pt.x, agent.pt.y);
          ctx.rotate(now * 0.0035);
          ctx.beginPath();
          ctx.arc(0, 0, nodeRadius + 8 * agent.pt.scale, 0, Math.PI * 2);
          ctx.strokeStyle = agent.color;
          ctx.lineWidth = 2.2 * agent.pt.scale;
          ctx.setLineDash([9, 6]);
          ctx.stroke();
          ctx.restore();

          // Orbiting plasma sparks
          const sparkCount = 4;
          for (let s = 0; s < sparkCount; s++) {
            const sparkAngle = now * 0.005 + (s * Math.PI * 2) / sparkCount;
            const sparkDist = nodeRadius + (12 + Math.sin(now * 0.008 + s) * 2.5) * agent.pt.scale;
            const sx = agent.pt.x + Math.cos(sparkAngle) * sparkDist;
            const sy = agent.pt.y + Math.sin(sparkAngle) * sparkDist;
            ctx.beginPath();
            ctx.arc(sx, sy, 3 * agent.pt.scale, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.shadowColor = agent.color;
            ctx.shadowBlur = 14;
            ctx.fill();
            ctx.shadowBlur = 0;
          }

          // 3D Spherical body
          const nodeGrad = ctx.createRadialGradient(
            agent.pt.x - nodeRadius * 0.35,
            agent.pt.y - nodeRadius * 0.35,
            nodeRadius * 0.08,
            agent.pt.x,
            agent.pt.y,
            nodeRadius
          );
          nodeGrad.addColorStop(0, "#ffffff");
          nodeGrad.addColorStop(0.18, "#ffffff");
          nodeGrad.addColorStop(0.48, agent.color);
          nodeGrad.addColorStop(0.85, hexToRgba(agent.color, 0.8));
          nodeGrad.addColorStop(1, "#030712");

          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, nodeRadius, 0, Math.PI * 2);
          ctx.fillStyle = nodeGrad;
          ctx.shadowColor = agent.color;
          ctx.shadowBlur = 48;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Rim
          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, nodeRadius, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";
          ctx.lineWidth = 2 * agent.pt.scale;
          ctx.stroke();

          // Inner ring
          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, nodeRadius + 3, 0, Math.PI * 2);
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1.5;
          ctx.shadowColor = agent.color;
          ctx.shadowBlur = 16;
          ctx.stroke();
          ctx.shadowBlur = 0;

          // Typography
          ctx.fillStyle = "#ffffff";
          ctx.font = `900 ${Math.max(12, Math.round(15 * agent.pt.scale))}px Inter, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.shadowColor = "rgba(0, 0, 0, 0.9)";
          ctx.shadowBlur = 6;
          ctx.fillText(agent.label, agent.pt.x, agent.pt.y);
          ctx.shadowBlur = 0;

          // RUNNING badge
          const badgeText = "⚡ RUNNING";
          const badgeFontSize = Math.max(9, Math.round(10 * agent.pt.scale));
          ctx.font = `800 ${badgeFontSize}px Inter, sans-serif`;
          const textMetrics = ctx.measureText(badgeText);
          const badgeW = textMetrics.width + 16 * agent.pt.scale;
          const badgeH = 18 * agent.pt.scale;
          const badgeX = agent.pt.x - badgeW / 2;
          const badgeY = agent.pt.y + nodeRadius + 9 * agent.pt.scale;

          drawRoundedRect(ctx, badgeX, badgeY, badgeW, badgeH, badgeH / 2);
          ctx.fillStyle = "rgba(10, 20, 35, 0.92)";
          ctx.fill();
          ctx.strokeStyle = agent.color;
          ctx.lineWidth = 1.8;
          ctx.shadowColor = agent.color;
          ctx.shadowBlur = 12;
          ctx.stroke();
          ctx.shadowBlur = 0;

          ctx.fillStyle = "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(badgeText, agent.pt.x, badgeY + badgeH / 2);
        } else {
          // Idle state
          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, nodeRadius + 3, 0, Math.PI * 2);
          ctx.strokeStyle = hexToRgba(agent.color, 0.4);
          ctx.lineWidth = 1;
          ctx.stroke();

          const nodeGrad = ctx.createRadialGradient(
            agent.pt.x - nodeRadius * 0.3,
            agent.pt.y - nodeRadius * 0.3,
            nodeRadius * 0.1,
            agent.pt.x,
            agent.pt.y,
            nodeRadius
          );
          nodeGrad.addColorStop(0, "#ffffff");
          nodeGrad.addColorStop(0.35, agent.color);
          nodeGrad.addColorStop(1, "#070c18");

          ctx.beginPath();
          ctx.arc(agent.pt.x, agent.pt.y, nodeRadius, 0, Math.PI * 2);
          ctx.fillStyle = nodeGrad;
          ctx.shadowColor = agent.color;
          ctx.shadowBlur = 8;
          ctx.fill();
          ctx.shadowBlur = 0;

          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${Math.max(8, Math.round(9 * agent.pt.scale))}px Inter, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(agent.label, agent.pt.x, agent.pt.y);

          ctx.font = `${Math.max(7, Math.round(8 * agent.pt.scale))}px Inter, sans-serif`;
          ctx.fillStyle = "rgba(226, 232, 240, 0.7)";
          ctx.fillText("READY", agent.pt.x, agent.pt.y + nodeRadius + 11);
        }
      });

      renderedAgentsRef.current = currentRenderedPointers;
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
      canvas.removeEventListener("click", handleClick);
    };
  }, []); // Run once on mount to keep box size completely static

  return (
    <div className="orbital-canvas-wrapper">
      <canvas ref={canvasRef} className="orbital-canvas" />
      <div className="orbital-overlay-info">
        <div className={`orbital-badge ${anyRunning ? "running" : ""}`}>
          <span className={`pulse-dot ${anyRunning ? "active" : ""}`} />
          <span>
            {currentRunningAgent
              ? `AGENT RUNNING: ${currentRunningAgent.name.toUpperCase()}`
              : isProcessing
              ? "DISPATCHING PACKETS"
              : "SYSTEM IDLE"}
          </span>
        </div>
        <div className="orbital-hint">
          {anyRunning
            ? "⚡ Active agent ball is enlarged and highlighted · Click any ball to focus"
            : "Hover to tilt · Click any agent ball to activate & inspect"}
        </div>
      </div>
    </div>
  );
}
