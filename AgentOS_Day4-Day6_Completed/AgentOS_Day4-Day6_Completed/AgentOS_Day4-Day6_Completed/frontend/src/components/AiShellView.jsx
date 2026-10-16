import { useState, useEffect, useRef } from "react";
import {
  Send,
  Zap,
  Sliders,
  ChevronDown,
  ChevronUp,
  Terminal,
  Activity,
  Copy,
  Check,
  RotateCcw,
  Sparkles,
  Bot,
  AlertTriangle,
  Flame,
  Clock,
  Code,
  Radio,
  Mic,
  MicOff,
  Image as ImageIcon,
  ExternalLink,
  Download,
  Layers,
  FlaskConical,
} from "lucide-react";
import OrbitalCore3D from "./OrbitalCore3D";
import { playDispatchSound, playSuccessSound, playAlertSound, playCyberClick } from "../utils/audio";

export default function AiShellView({
  api,
  metrics,
  stats,
  agents = [],
  scheduler = "fifo",
  onSwitchScheduler,
  onTaskCompleted,
  events = [],
}) {
  const [prompt, setPrompt] = useState("");
  const [priority, setPriority] = useState(5);
  const [estimatedTokens, setEstimatedTokens] = useState(256);
  const [complexity, setComplexity] = useState(1);
  const [riskLevel, setRiskLevel] = useState(1);
  const [selectedAgentType, setSelectedAgentType] = useState("auto");
  const [deadline, setDeadline] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // User image uploading state
  const [uploadedImage, setUploadedImage] = useState(null); // { name, sizeText, previewUrl, serverUrl }
  const [uploadingImage, setUploadingImage] = useState(false);
  const fileInputRef = useRef(null);

  // Route preview
  const [routePreview, setRoutePreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);


  // Terminal state
  const [terminalInput, setTerminalInput] = useState("");
  const [terminalHistory, setTerminalHistory] = useState([
    {
      type: "system",
      text: "AgentOS AI Shell Initialized [v0.4.0]\nType 'help' for command reference or enter a task prompt.\nSafe sandbox enforcement: active.",
      time: new Date().toLocaleTimeString(),
    },
  ]);
  const [busy, setBusy] = useState(false);
  const [copiedTerminal, setCopiedTerminal] = useState(false);
  const terminalEndRef = useRef(null);

  // Active executing task for 3D visualizer
  const [activeTaskAgent, setActiveTaskAgent] = useState(null);

  // Voice Input (Web Speech API) State
  const SpeechRecognition = typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;
  const [isListening, setIsListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("");
  const [voiceStatusType, setVoiceStatusType] = useState("info");
  const recognitionRef = useRef(null);
  const promptRef = useRef(prompt);
  promptRef.current = prompt;

  const stopVoiceInput = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
    }
    setIsListening(false);
  };

  const toggleVoiceInput = () => {
    if (isListening) {
      stopVoiceInput();
      setVoiceStatus("Voice input stopped. Review or edit your prompt before dispatching.");
      setVoiceStatusType("success");
      return;
    }

    if (!SpeechRecognition) {
      setVoiceStatus("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari, or type your prompt.");
      setVoiceStatusType("error");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = navigator.language || "en-US";
      recognition.maxAlternatives = 1;
      recognitionRef.current = recognition;

      const baseText = promptRef.current ? promptRef.current.trim() + " " : "";

      recognition.onstart = () => {
        setIsListening(true);
        setVoiceStatus("Listening... Speak your task clearly.");
        setVoiceStatusType("listening");
        playCyberClick();
      };

      recognition.onresult = (event) => {
        let interim = "";
        let final = "";

        for (let i = 0; i < event.results.length; ++i) {
          const piece = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += piece;
          } else {
            interim += piece;
          }
        }

        const currentFull = (baseText + final + (interim ? " " + interim : "")).trim();
        setPrompt(currentFull);

        if (interim) {
          setVoiceStatus(`Transcribing: "${interim}"`);
          setVoiceStatusType("listening");
        } else if (final) {
          setVoiceStatus("Transcription updated. You can review or edit before dispatching.");
          setVoiceStatusType("success");
        }
      };

      recognition.onerror = (event) => {
        setIsListening(false);
        if (event.error === "not-allowed") {
          setVoiceStatus("Microphone permission denied. Enable microphone access in browser settings.");
          setVoiceStatusType("error");
        } else if (event.error === "no-speech") {
          setVoiceStatus("No speech detected. Click the microphone to try again.");
          setVoiceStatusType("info");
        } else if (event.error === "network") {
          setVoiceStatus("Speech recognition network error. Please verify network connectivity.");
          setVoiceStatusType("error");
        } else {
          setVoiceStatus(`Speech recognition error: ${event.error}`);
          setVoiceStatusType("error");
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        if (promptRef.current.trim()) {
          setVoiceStatus("Transcription ready. Review or edit, then click Dispatch to Scheduler or Instant Run.");
          setVoiceStatusType("success");
        }
      };

      recognition.start();
    } catch (err) {
      setIsListening(false);
      setVoiceStatus(`Failed to start speech recognition: ${err.message}`);
      setVoiceStatusType("error");
    }
  };

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_) {}
      }
    };
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalHistory]);

  // Debounced route preview when prompt changes
  useEffect(() => {
    if (!prompt.trim() || prompt.length < 5) {
      setRoutePreview(null);
      return;
    }
    const timer = setTimeout(async () => {
      setPreviewLoading(true);
      try {
        const data = await api("/api/route", {
          method: "POST",
          body: JSON.stringify({ prompt: prompt.trim() }),
        });
        setRoutePreview(data);
      } catch {
        setRoutePreview(null);
      } finally {
        setPreviewLoading(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [prompt, api]);

  const appendTerminal = (type, text, imageUrl = null) => {
    setTerminalHistory((prev) => [
      ...prev,
      { type, text, imageUrl, time: new Date().toLocaleTimeString() },
    ]);
  };

  // Image Upload Handling
  const handleImageFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processAndUploadImage(file);
    e.target.value = "";
  };

  const handleDropFile = async (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      await processAndUploadImage(file);
    }
  };

  const processAndUploadImage = async (file) => {
    setUploadingImage(true);
    const sizeKB = Math.round(file.size / 1024);
    const sizeText = sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64Data = event.target.result;
      setUploadedImage({
        name: file.name,
        sizeText,
        previewUrl: base64Data,
        serverUrl: null,
      });

      try {
        const uploadRes = await api("/api/upload/image", {
          method: "POST",
          body: JSON.stringify({
            image: base64Data,
            filename: file.name,
          }),
        });
        if (uploadRes?.url) {
          setUploadedImage((prev) => (prev ? { ...prev, serverUrl: uploadRes.url } : null));
          playSuccessSound();
        }
      } catch (err) {
        console.warn("Backend image upload fallback to local preview:", err.message);
      } finally {
        setUploadingImage(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const clearUploadedImage = () => {
    setUploadedImage(null);
  };

  // Poll task completion
  const pollTask = async (taskId) => {
    const deadlineTime = Date.now() + 120000;
    while (Date.now() < deadlineTime) {
      const item = await api(`/task/${encodeURIComponent(taskId)}`);
      if (["done", "failed", "blocked"].includes(item.status)) {
        setActiveTaskAgent(null);
        const result = item.result;
        const statusText = `[${item.status.toUpperCase()}] · ${item.agent || "Agent"}\nTask ID: ${taskId}\nLatency: ${result?.latency_seconds ? Number(result.latency_seconds).toFixed(2) + "s" : "—"} · Tokens: ${result?.tokens_used || 0}\n\n${result?.response || result?.error || "Task completed."}`;
        
        appendTerminal(item.status === "done" ? "output-success" : "output-error", statusText, item.image_url || result?.image_url);
        if (item.status === "done") {
          playSuccessSound();
        } else {
          playAlertSound();
        }
        if (onTaskCompleted) onTaskCompleted();
        return;
      }
      await new Promise((r) => setTimeout(r, 450));
    }
    setActiveTaskAgent(null);
    appendTerminal("output-warning", `Task ${taskId} timed out waiting for completion.`);
  };

  // Asynchronous Dispatch
  const handleDispatch = async () => {
    if (!prompt.trim() || busy) return;
    const taskPrompt = prompt.trim();
    const targetAgent = selectedAgentType !== "auto" ? selectedAgentType : (routePreview?.agent || "GeneralAgent");
    setActiveTaskAgent(targetAgent);
    setBusy(true);
    playDispatchSound();
    
    const cmdText = uploadedImage
      ? `dispatch --priority ${priority} [IMAGE: ${uploadedImage.name}] "${taskPrompt}"`
      : `dispatch --priority ${priority} "${taskPrompt}"`;
    appendTerminal("cmd", cmdText, uploadedImage?.previewUrl);

    try {
      const payload = {
        prompt: taskPrompt,
        priority: Number(priority),
        estimated_tokens: Number(estimatedTokens),
        complexity: Number(complexity),
        risk_level: Number(riskLevel),
        deadline_s: deadline ? Number(deadline) : null,
        agent_type: selectedAgentType === "auto" ? null : selectedAgentType,
        image_url: uploadedImage?.serverUrl || uploadedImage?.previewUrl || null,
      };

      const res = await api("/task", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (res.is_composite && res.subtask_ids?.length) {
        setActiveTaskAgent(res.agent || targetAgent);
        appendTerminal(
          "output-info",
          `🔀 COMPOSITE JOB QUEUED · ${res.subtasks?.length} Sub-Tasks Scheduled\nAgents: ${res.agent}\nScheduler: ${res.scheduler} (Priority ${res.priority})\nDispatching across agents through AgentOS job scheduling…`
        );
        for (const sub of res.subtasks) {
          appendTerminal("system", `[WAITING] Sub-task #${sub.index} (${sub.agent}): ${sub.prompt}`);
          await pollTask(sub.task_id);
        }
      } else {
        setActiveTaskAgent(res.agent || targetAgent);
        appendTerminal(
          "output-info",
          `QUEUED · Agent: ${res.agent}\nTask ID: ${res.task_id}\nScheduler: ${res.scheduler} (Priority ${res.priority})\nAwaiting agent execution…`
        );
        await pollTask(res.task_id);
      }
    } catch (err) {
      appendTerminal("output-error", `Dispatch Failed: ${err.message}`);
      playAlertSound();
      setActiveTaskAgent(null);
    } finally {
      setBusy(false);
      setActiveTaskAgent(null);
    }
  };

  // Enqueue Task Without Immediate Auto-Run (Hold in Queue for Scheduling)
  const handleEnqueueOnly = async () => {
    if (!prompt.trim()) return;
    const taskPrompt = prompt.trim();
    const targetAgent = selectedAgentType !== "auto" ? selectedAgentType : (routePreview?.agent || "GeneralAgent");
    playCyberClick();
    
    const cmdText = uploadedImage
      ? `enqueue --priority ${priority} [IMAGE: ${uploadedImage.name}] "${taskPrompt}"`
      : `enqueue --priority ${priority} "${taskPrompt}"`;
    appendTerminal("cmd", cmdText, uploadedImage?.previewUrl);

    try {
      const payload = {
        prompt: taskPrompt,
        priority: Number(priority),
        estimated_tokens: Number(estimatedTokens),
        complexity: Number(complexity),
        risk_level: Number(riskLevel),
        deadline_s: deadline ? Number(deadline) : null,
        agent_type: selectedAgentType === "auto" ? null : selectedAgentType,
        image_url: uploadedImage?.serverUrl || uploadedImage?.previewUrl || null,
        enqueue_only: true,
      };

      const res = await api("/task", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      appendTerminal(
        "output-info",
        `📥 ENQUEUED TO QUEUE (Held for Scheduler)\nTask ID: ${res.task_id}\nPriority: P${res.priority} | Agent: ${res.agent}\nActive Policy: ${res.scheduler}\n\nTask placed in queue. Go to the 'Scheduler' tab to inspect, switch policies (FIFO, Priority, Round Robin), or click 'Step (1 Task)' / 'Run All Queue'.`
      );
      playSuccessSound();
      if (onTaskCompleted) onTaskCompleted();
    } catch (err) {
      appendTerminal("output-error", `Enqueue Failed: ${err.message}`);
      playAlertSound();
    }
  };

  // Synchronous Instant Run
  const handleInstantRun = async () => {
    if (!prompt.trim() || busy) return;
    const taskPrompt = prompt.trim();
    const targetAgent = selectedAgentType !== "auto" ? selectedAgentType : (routePreview?.agent || "GeneralAgent");
    setActiveTaskAgent(targetAgent);
    setBusy(true);
    playDispatchSound();
    
    const cmdText = uploadedImage
      ? `run:instant [IMAGE: ${uploadedImage.name}] "${taskPrompt}"`
      : `run:instant "${taskPrompt}"`;
    appendTerminal("cmd", cmdText, uploadedImage?.previewUrl);

    try {
      const payload = {
        prompt: taskPrompt,
        priority: Number(priority),
        estimated_tokens: Number(estimatedTokens),
        complexity: Number(complexity),
        risk_level: Number(riskLevel),
        agent_type: selectedAgentType === "auto" ? null : selectedAgentType,
        image_url: uploadedImage?.serverUrl || uploadedImage?.previewUrl || null,
      };

      const res = await api("/api/task", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setActiveTaskAgent(res.agent || targetAgent);
      if (res.is_composite) {
        const outText = `[COMPOSITE WORKFLOW COMPLETE] · ${res.agent}\nMakespan: ${res.latency_seconds ? Number(res.latency_seconds).toFixed(2) + "s" : "—"} · Tokens: ${res.tokens_used || 0} · Backend: ${res.llm_backend || "unknown"}\n\n${res.response || "Multi-agent scheduled execution completed."}`;
        appendTerminal("output-success", outText, res.image_url);
      } else {
        const outText = `[${res.status?.toUpperCase() || "DONE"}] · ${res.agent}\nLatency: ${res.latency_seconds ? Number(res.latency_seconds).toFixed(2) + "s" : "—"} · Tokens: ${res.tokens_used || 0} · Backend: ${res.llm_backend || "unknown"}\n\n${res.response || res.error || "Execution completed."}`;
        appendTerminal(res.error ? "output-error" : "output-success", outText, res.image_url);
      }
      playSuccessSound();
      if (onTaskCompleted) onTaskCompleted();
      await new Promise((r) => setTimeout(r, 1200));
    } catch (err) {
      appendTerminal("output-error", `Execution Failed: ${err.message}`);
      playAlertSound();
    } finally {
      setActiveTaskAgent(null);
      setBusy(false);
    }
  };

  // Terminal Command Execution
  const handleTerminalSubmit = async (e) => {
    e?.preventDefault();
    const raw = terminalInput.trim();
    if (!raw || busy) return;
    setTerminalInput("");
    appendTerminal("cmd", raw);
    playCyberClick();

    const first = raw.split(/\s+/, 1)[0].toLowerCase();
    const rest = raw.slice(first.length).trim();

    if (first === "clear") {
      setTerminalHistory([]);
      return;
    }

    if (first === "help") {
      appendTerminal(
        "system",
        "AgentOS CLI Commands:\n" +
          "  run <prompt>              - Execute prompt through AgentOS scheduler\n" +
          "  status                    - Inspect runtime health and host metrics\n" +
          "  history                   - Show stored task summary\n" +
          "  scheduler <policy>        - Switch policy: fifo | priority | roundrobin | resourceaware\n" +
          "  route <prompt>            - Test task routing engine without executing\n" +
          "  search <concept>          - Semantic search across intent, workspace & tasks\n" +
          "  step                      - Manually step scheduler runtime to process next task\n" +
          "  clear                     - Clear terminal buffer\n" +
          "\nAny unrecognized input is submitted as an autonomous task prompt."
      );
      return;
    }

    if (first === "search") {
      if (!rest) {
        appendTerminal("output-warning", "Usage: search <concept or prompt>");
        return;
      }
      try {
        const res = await api(`/api/search/semantic?q=${encodeURIComponent(rest)}`);
        const intent = res.semantic_intent;
        let out = `🧠 Semantic Intent Analysis:\n` +
          `  Capability: ${intent.capability} (Confidence: ${(intent.confidence * 100).toFixed(1)}%)\n`;
        if (res.workspace_matches?.length) {
          out += `\n📁 Workspace Semantic Matches:\n` +
            res.workspace_matches.map(m => `  • [${(m.score * 100).toFixed(0)}%] ${m.path}\n    "${m.snippet}"`).join("\n");
        }
        if (res.task_matches?.length) {
          out += `\n📋 Semantically Related Tasks:\n` +
            res.task_matches.map(m => `  • [${(m.score * 100).toFixed(0)}%] ${m.task_id} (${m.agent}): ${m.prompt}`).join("\n");
        }
        appendTerminal("output-info", out);
      } catch (err) {
        appendTerminal("output-error", `Search error: ${err.message}`);
      }
      return;
    }

    if (first === "status") {
      try {
        const [s, m] = await Promise.all([api("/api/status"), api("/metrics")]);
        appendTerminal("output-info", JSON.stringify({ ...s, metrics: m }, null, 2));
      } catch (err) {
        appendTerminal("output-error", `Status error: ${err.message}`);
      }
      return;
    }

    if (first === "scheduler") {
      if (!rest) {
        appendTerminal("output-warning", "Usage: scheduler <fifo|priority|roundrobin|resourceaware>");
        return;
      }
      try {
        const res = await api("/scheduler", {
          method: "POST",
          body: JSON.stringify({ scheduler: rest.toLowerCase() }),
        });
        appendTerminal("output-success", `Scheduler switched to ${res.scheduler}`);
        if (onSwitchScheduler) onSwitchScheduler(rest.toLowerCase());
      } catch (err) {
        appendTerminal("output-error", `Scheduler change failed: ${err.message}`);
      }
      return;
    }

    if (first === "step") {
      try {
        const res = await api("/api/runtime/step", { method: "POST" });
        if (res.result) {
          appendTerminal("output-success", `Scheduler Step: Executed Task ${res.result.task_id} (${res.result.status}) via ${res.result.scheduler || scheduler}`);
          if (onTaskCompleted) onTaskCompleted();
        } else {
          appendTerminal("output-info", "Scheduler Step: Queue is empty. Use 'demo' or 'enqueue <prompt>' to add tasks.");
        }
      } catch (err) {
        appendTerminal("output-error", `Step error: ${err.message}`);
      }
      return;
    }

    if (first === "runall") {
      try {
        const res = await api("/api/runtime/run-all", { method: "POST" });
        if (res.executed_count > 0) {
          appendTerminal("output-success", `Executed ${res.executed_count} queued tasks through ${res.scheduler} scheduler.`);
          if (onTaskCompleted) onTaskCompleted();
        } else {
          appendTerminal("output-info", "Queue is empty. Type 'demo' to load a 4-task benchmark batch.");
        }
      } catch (err) {
        appendTerminal("output-error", `Run-all error: ${err.message}`);
      }
      return;
    }

    if (first === "demo") {
      try {
        const res = await api("/api/queue/demo-batch", { method: "POST" });
        appendTerminal("output-success", `${res.message}\nActive Policy: ${res.scheduler} | Queue Length: ${res.queue_length}\nType 'step' to run task-by-task or 'runall' to execute all.`);
        if (onTaskCompleted) onTaskCompleted();
      } catch (err) {
        appendTerminal("output-error", `Demo load error: ${err.message}`);
      }
      return;
    }

    if (first === "clearqueue") {
      try {
        const res = await api("/api/queue/clear", { method: "POST" });
        appendTerminal("output-info", `${res.message}`);
        if (onTaskCompleted) onTaskCompleted();
      } catch (err) {
        appendTerminal("output-error", `Clear error: ${err.message}`);
      }
      return;
    }

    if (first === "enqueue") {
      if (!rest) {
        appendTerminal("output-warning", "Usage: enqueue <prompt>");
        return;
      }
      try {
        const res = await api("/task", {
          method: "POST",
          body: JSON.stringify({ prompt: rest, priority: Number(priority), enqueue_only: true }),
        });
        appendTerminal("output-success", `📥 Enqueued Task ${res.task_id} (Priority P${res.priority}) into ${res.scheduler} queue.`);
        if (onTaskCompleted) onTaskCompleted();
      } catch (err) {
        appendTerminal("output-error", `Enqueue error: ${err.message}`);
      }
      return;
    }

    if (first === "route") {
      if (!rest) {
        appendTerminal("output-warning", "Usage: route <prompt>");
        return;
      }
      try {
        const res = await api("/api/route", {
          method: "POST",
          body: JSON.stringify({ prompt: rest }),
        });
        appendTerminal("output-info", `Route Decision:\nAgent: ${res.agent}\nCapability: ${res.capability}\nModel: ${res.model}`);
      } catch (err) {
        appendTerminal("output-error", `Route error: ${err.message}`);
      }
      return;
    }

    // Otherwise treat as task prompt
    const p = first === "run" ? rest : raw;
    setPrompt(p);
    const targetAgent = selectedAgentType !== "auto" ? selectedAgentType : (routePreview?.agent || "GeneralAgent");
    setActiveTaskAgent(targetAgent);
    setBusy(true);
    try {
      const res = await api("/task", {
        method: "POST",
        body: JSON.stringify({ prompt: p, priority: 5, estimated_tokens: 256, complexity: 1, risk_level: 1 }),
      });
      setActiveTaskAgent(res.agent || targetAgent);
      appendTerminal(
        "output-info",
        `QUEUED · Agent: ${res.agent}\nTask ID: ${res.task_id}\nScheduler: ${res.scheduler}\nAwaiting response…`
      );
      await pollTask(res.task_id);
    } catch (err) {
      appendTerminal("output-error", `Task error: ${err.message}`);
    } finally {
      setActiveTaskAgent(null);
      setBusy(false);
    }
  };

  const copyTerminalOutput = () => {
    const text = terminalHistory.map((h) => `[${h.time}] ${h.text}`).join("\n\n");
    navigator.clipboard.writeText(text);
    setCopiedTerminal(true);
    setTimeout(() => setCopiedTerminal(false), 2000);
  };

  const multiAgentTemplates = [
    {
      title: "🎯 Priority Preemption Test [P1 vs P10 vs P6]",
      badge: "Priority Test",
      desc: "Tests Priority Scheduler reordering (P10 preempts P6 & P1)",
      prompt:
        "[1] [P1] (GeneralAgent) Explain microkernel vs monolithic operating system architecture.\n[2] [P10] (SecurityAgent) Audit security policy sandbox boundaries and verify unauthorized command prevention.\n[3] [P6] (MonitoringAgent) Collect system CPU, RAM load, and queue depth telemetry.",
    },
    {
      title: "🔄 Round Robin Fair-Share Rotation",
      badge: "Round Robin",
      desc: "Alternates between File and Monitoring agents",
      prompt:
        "[1] (FileAgent) Count and list files in backend/agents directory.\n[2] (FileAgent) Verify if results/summary.csv exists.\n[3] (MonitoringAgent) Collect system CPU load metrics.\n[4] (MonitoringAgent) Report host memory percentage and active processes.",
    },
    {
      title: "⚡ 3-Agent System Audit",
      badge: "3 Agents",
      prompt:
        "[1] (MonitoringAgent) Collect system CPU, RAM load, and queue depth metrics.\n[2] (FileAgent) Count and list files in the backend directory.\n[3] (SecurityAgent) Inspect sandbox policy boundaries and security risks.",
    },
    {
      title: "⚡ 2-Agent Workspace & Plan",
      badge: "2 Agents",
      prompt:
        "1. [FileAgent] Search for python test files in the backend.\n2. [PlanningAgent] Generate a structured job orchestration plan for scheduler evaluation.",
    },
    {
      title: "⚡ 1-Agent Multi-Question File Audit",
      badge: "1 Agent",
      prompt:
        "[1] (FileAgent) Count files in backend/agents directory.\n[2] (FileAgent) Verify if results/summary.csv exists.",
    },
    {
      title: "🎨 2-Agent Architecture & Visual",
      badge: "2 Agents",
      prompt:
        "[1] (PlanningAgent) Outline the AgentOS microkernel subsystem layout.\n[2] (ImageAgent) Generate image of AgentOS system architecture diagram.",
    },
    {
      title: "⚡ Numbered Natural Questions",
      badge: "Auto-Routed",
      prompt:
        "1. What are the current CPU utilization and RAM metrics?\n2. Check if there are any unauthorized security risk commands.\n3. Summarize the role of the FIFO and Priority schedulers.",
    },
  ];

  const promptSuggestions = [
    "generate image of AgentOS system architecture diagram",
    "create an image of cyberpunk orbital core",
    "create a file named notes/hello.txt with content: Hello from AgentOS!",
    "Collect CPU, memory, and task latency metrics and detect anomalies",
    "Break down a web app migration project into subtasks and assign agents",
    "Explain how AgentOS task router selects specialized agents",
    "Audit security policy boundaries and check unauthorized commands",
  ];

  return (
    <div className="shell-workspace">
      {/* 3D Visualizer & Quick Telemetry Row */}
      <div className="visualizer-row glass-panel">
        <div className="vis-canvas-container">
          <OrbitalCore3D
            agents={agents}
            activeAgent={activeTaskAgent}
            isProcessing={busy || Boolean(activeTaskAgent)}
            metrics={metrics}
            scheduler={scheduler}
            onSelectAgent={(agentName) => {
              playCyberClick();
              setActiveTaskAgent((prev) => (prev === agentName ? null : agentName));
            }}
          />
          <div className="vis-controls-bar">
            <div className="vis-controls-title">
              <Radio size={13} className="text-cyan animate-pulse" />
              <span>Orbital Agent Activity:</span>
            </div>
            <div className="vis-agent-pills">
              <button
                type="button"
                className={`vis-pill ${!activeTaskAgent && !busy ? "active" : ""}`}
                onClick={() => {
                  playCyberClick();
                  setActiveTaskAgent(null);
                }}
                title="System Idle: All balls at rest size"
              >
                ● System Idle
              </button>
              {[
                { id: "GeneralAgent", label: "GEN", name: "General" },
                { id: "FileAgent", label: "FILE", name: "File" },
                { id: "SecurityAgent", label: "SEC", name: "Security" },
                { id: "MonitoringAgent", label: "MON", name: "Monitor" },
                { id: "PlanningAgent", label: "PLAN", name: "Plan" },
                { id: "ImageAgent", label: "IMG", name: "Image" },
              ].map((ag) => {
                const isAgActive =
                  activeTaskAgent &&
                  (activeTaskAgent.toLowerCase().includes(ag.label.toLowerCase()) ||
                    activeTaskAgent.toLowerCase().includes(ag.name.toLowerCase()));
                return (
                  <button
                    key={ag.id}
                    type="button"
                    className={`vis-pill agent-${ag.label.toLowerCase()} ${isAgActive ? "active running" : ""}`}
                    onClick={() => {
                      playCyberClick();
                      setActiveTaskAgent(isAgActive ? null : ag.id);
                    }}
                    title={`Highlight ${ag.name}Agent ball (make bigger & highlighted)`}
                  >
                    ⚡ {ag.label} {isAgActive ? "RUNNING" : ""}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Realtime KPI Strip */}
        <div className="vis-metrics-strip">
          <div className="kpi-card">
            <span className="kpi-label">CPU UTILIZATION</span>
            <strong className="kpi-val text-cyan">
              {metrics ? `${metrics.cpu_percent.toFixed(1)}%` : "—"}
            </strong>
            <div className="mini-progress-bar">
              <i style={{ width: `${Math.min(100, metrics?.cpu_percent || 0)}%` }} />
            </div>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">RAM LOAD</span>
            <strong className="kpi-val text-violet">
              {metrics ? `${metrics.ram_percent.toFixed(1)}%` : "—"}
            </strong>
            <div className="mini-progress-bar">
              <i
                style={{
                  width: `${Math.min(100, metrics?.ram_percent || 0)}%`,
                  background: "linear-gradient(90deg, #8b5cf6, #ec4899)",
                }}
              />
            </div>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">LIFETIME TOKENS</span>
            <strong className="kpi-val text-emerald">
              {(metrics?.tokens_total ?? 0).toLocaleString()}
            </strong>
            <span className="kpi-sub">processed tokens</span>
          </div>

          <div className="kpi-card">
            <span className="kpi-label">QUEUE DEPTH</span>
            <strong className="kpi-val text-amber">{metrics?.queue_length ?? 0}</strong>
            <span className="kpi-sub">{scheduler.toUpperCase()} scheduler</span>
          </div>
        </div>
      </div>

      {/* Main Two-Column Interaction Grid */}
      <div className="shell-grid">
        {/* Left Column: Task Dispatcher & Studio */}
        <section className="task-dispatcher-card glass-panel">
          <div className="panel-top-title">
            <div className="title-with-icon">
              <Sparkles size={16} className="text-cyan" />
              <div>
                <h3>Interactive Task Dispatcher</h3>
                <p>Compose multi-agent indexed prompts and schedule tasks with dynamic agent routing</p>
              </div>
            </div>
          </div>

          {/* Multi-Agent Indexed Prompt Templates */}
          <div className="multi-agent-templates-container">
            <div className="template-strip-header">
              <Sparkles size={13} className="text-cyan" />
              <span>Multi-Agent / Multi-Question Scheduling Templates:</span>
            </div>
            <div className="chips-list">
              {multiAgentTemplates.map((t, idx) => (
                <button
                  key={idx}
                  className="prompt-chip multi-agent-chip"
                  onClick={() => {
                    playCyberClick();
                    setPrompt(t.prompt);
                  }}
                  title={t.desc}
                >
                  <span className="chip-badge">{t.badge}</span>
                  <span>{t.title}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Prompt Suggestion Chips */}
          <div className="suggestion-chips-container">
            <span className="suggestion-title">Single Prompts:</span>
            <div className="chips-list">
              {promptSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  className="prompt-chip"
                  onClick={() => {
                    playCyberClick();
                    setPrompt(s);
                  }}
                >
                  {s.slice(0, 36)}…
                </button>
              ))}
            </div>
          </div>

          {/* Prompt Textarea */}
          <div className="prompt-input-wrapper">
            <div className="prompt-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label htmlFor="task-prompt" style={{ margin: 0 }}>TASK PROMPT / GOAL (1 OR MORE INDEXED QUESTIONS)</label>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
                  style={{ display: "none" }}
                  onChange={handleImageFileSelect}
                />
                <button
                  type="button"
                  className={`btn-image-toggle ${uploadedImage ? "active" : ""}`}
                  onClick={() => fileInputRef.current?.click()}
                  title="Upload an image to attach or analyze"
                  disabled={busy || uploadingImage}
                >
                  <ImageIcon size={13} className="text-cyan" />
                  <span>{uploadingImage ? "Uploading…" : uploadedImage ? "Image Attached" : "Upload Image"}</span>
                </button>
                <button
                  type="button"
                  className={`btn-voice-toggle ${isListening ? "listening" : ""} ${!SpeechRecognition ? "unsupported" : ""}`}
                  onClick={toggleVoiceInput}
                  title={SpeechRecognition ? (isListening ? "Stop listening" : "Start voice task input") : "Speech recognition unsupported in this browser"}
                  aria-label={isListening ? "Stop listening" : "Start voice input"}
                  disabled={busy}
                >
                  {isListening ? <MicOff size={13} className="text-rose" /> : <Mic size={13} className="text-cyan" />}
                  <span>{isListening ? "Stop Listening" : "Voice Input"}</span>
                </button>
              </div>
            </div>

            {/* Attached Image Preview Card */}
            {uploadedImage && (
              <div className="attached-image-preview-card">
                <div className="attached-img-left">
                  <img src={uploadedImage.previewUrl} alt="Attached input" className="attached-img-thumb" />
                  <div className="attached-img-meta">
                    <span className="attached-badge">IMAGE ATTACHED</span>
                    <span className="attached-filename">{uploadedImage.name} ({uploadedImage.sizeText})</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-remove-attached-img"
                  onClick={clearUploadedImage}
                  title="Remove attached image"
                >
                  ✕
                </button>
              </div>
            )}

            <textarea
              id="task-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDropFile}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                  handleDispatch();
                }
              }}
              placeholder="Enter a task or multi-question prompt, e.g.:&#10;• generate image of AgentOS system architecture diagram&#10;• create an image of cyberpunk orbital core&#10;• [1] (MonitoringAgent) Check CPU telemetry&#10;• [2] (ImageAgent) Draw system diagram"
              disabled={busy}
              rows={5}
            />
            {voiceStatus && (
              <div className={`voice-feedback-banner voice-${voiceStatusType}`}>
                <span>{voiceStatus}</span>
                {isListening && (
                  <button type="button" className="voice-banner-stop" onClick={stopVoiceInput}>
                    Stop
                  </button>
                )}
              </div>
            )}
            <div className="textarea-footer">
              <span className="key-hint">Press Ctrl+Enter to Dispatch · Multi-agent indexed questions supported</span>
              <span className="char-count">{prompt.length} chars</span>
            </div>
          </div>

          {/* Live Route Preview Pill / Composite Preview Card */}
          {routePreview && (
            <div className={`route-preview-banner ${routePreview.is_composite ? "composite-preview-card" : ""}`}>
              <div className="preview-top-row" style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <Bot size={14} className="text-cyan animate-pulse" />
                <span style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8" }}>
                  {routePreview.is_composite
                    ? `🔀 Multi-Question Composite Task (${routePreview.subtasks?.length} Sub-Tasks Indexed):`
                    : "Predicted Route:"}
                </span>
                <strong className="text-cyan">{routePreview.agent}</strong>
                <span className="tag-capability">{routePreview.capability}</span>
                <span className="tag-model">{routePreview.model}</span>
                <span className="tag-scheduler" style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "6px", background: "rgba(16, 185, 129, 0.15)", border: "1px solid rgba(16, 185, 129, 0.4)", color: "#10b981", fontWeight: "700" }}>
                  Active: {scheduler.toUpperCase()}
                </span>
              </div>
              {routePreview.is_composite && routePreview.subtasks && (
                <div className="composite-subtasks-preview" style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {routePreview.subtasks.map((st, i) => (
                    <div
                      key={i}
                      className="composite-subtask-item"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "6px 10px",
                        background: "rgba(0, 0, 0, 0.35)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "8px",
                        fontSize: "11px",
                      }}
                    >
                      <span style={{ fontWeight: "800", color: "#00f0ff", minWidth: "24px" }}>#{st.index}</span>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "rgba(139, 92, 246, 0.2)",
                          border: "1px solid rgba(139, 92, 246, 0.4)",
                          color: "#c084fc",
                          fontWeight: "700",
                          fontSize: "10px",
                        }}
                      >
                        {st.agent_name}
                      </span>
                      <span style={{ color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {st.prompt}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Quick Priority Shortcut Strip */}
          <div className="quick-priority-bar" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "10px 0 6px 0", padding: "6px 12px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.07)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: "700", color: "#94a3b8" }}>
              <Sliders size={13} className="text-cyan" />
              <span>Priority Quick-Select:</span>
            </div>
            <div style={{ display: "flex", gap: "6px" }}>
              {[
                { val: 1, label: "P1 (Low)", color: "#00f0ff", bg: "rgba(0, 240, 255, 0.15)" },
                { val: 5, label: "P5 (Normal)", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
                { val: 10, label: "P10 (Urgent/Preempt)", color: "#f43f5e", bg: "rgba(244, 63, 94, 0.2)" },
              ].map((p) => (
                <button
                  key={p.val}
                  type="button"
                  className={`quick-prio-btn ${priority === p.val ? "active" : ""}`}
                  style={{
                    padding: "3px 10px",
                    fontSize: "11px",
                    borderRadius: "6px",
                    border: priority === p.val ? `1px solid ${p.color}` : "1px solid rgba(255, 255, 255, 0.1)",
                    background: priority === p.val ? p.bg : "rgba(0, 0, 0, 0.35)",
                    color: priority === p.val ? p.color : "#94a3b8",
                    fontWeight: "700",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onClick={() => {
                    playCyberClick();
                    setPriority(p.val);
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Parameters Accordion */}
          <div className="advanced-accordion" style={{ margin: "6px 0 12px 0", borderRadius: "8px", border: "1px solid rgba(0, 240, 255, 0.25)", background: "rgba(0, 240, 255, 0.03)" }}>
            <button
              type="button"
              className="advanced-toggle-btn"
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                background: "transparent",
                border: "none",
                color: "#e2e8f0",
                fontSize: "12px",
                fontWeight: "700",
                cursor: "pointer",
              }}
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Sliders size={14} className="text-cyan" />
                <span>⚙️ Advanced Settings & Scheduling Parameters</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", background: priority >= 8 ? "rgba(244, 63, 94, 0.25)" : priority >= 5 ? "rgba(245, 158, 11, 0.25)" : "rgba(0, 240, 255, 0.25)", color: priority >= 8 ? "#f43f5e" : priority >= 5 ? "#f59e0b" : "#00f0ff", fontWeight: "800" }}>
                  Priority: P{priority} · {estimatedTokens} Tokens
                </span>
                {showAdvanced ? <ChevronUp size={14} className="text-cyan" /> : <ChevronDown size={14} className="text-cyan" />}
              </div>
            </button>

            {showAdvanced && (
              <div className="advanced-drawer">
                <div className="drawer-grid">
                  {/* Priority Slider */}
                  <div className="slider-control">
                    <div className="slider-label-row">
                      <span>PRIORITY (1-10)</span>
                      <strong className={`badge-pill ${priority >= 8 ? "bg-rose" : priority >= 5 ? "bg-amber" : "bg-cyan"}`}>
                        P{priority}
                      </strong>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={10}
                      value={priority}
                      onChange={(e) => setPriority(Number(e.target.value))}
                    />
                  </div>

                  {/* Estimated Tokens Slider */}
                  <div className="slider-control">
                    <div className="slider-label-row">
                      <span>ESTIMATED TOKENS</span>
                      <strong className="badge-pill bg-violet">{estimatedTokens}</strong>
                    </div>
                    <input
                      type="range"
                      min={64}
                      max={4096}
                      step={64}
                      value={estimatedTokens}
                      onChange={(e) => setEstimatedTokens(Number(e.target.value))}
                    />
                  </div>

                  {/* Complexity */}
                  <div className="slider-control">
                    <div className="slider-label-row">
                      <span>COMPLEXITY (1-5)</span>
                      <strong className="badge-pill">{complexity}</strong>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={5}
                      value={complexity}
                      onChange={(e) => setComplexity(Number(e.target.value))}
                    />
                  </div>

                  {/* Risk Level */}
                  <div className="slider-control">
                    <div className="slider-label-row">
                      <span>RISK LEVEL (1-5)</span>
                      <strong className={`badge-pill ${riskLevel >= 4 ? "bg-rose" : "bg-emerald"}`}>
                        {riskLevel}
                      </strong>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={5}
                      value={riskLevel}
                      onChange={(e) => setRiskLevel(Number(e.target.value))}
                    />
                  </div>

                  {/* Target Agent Lock */}
                  <div className="select-control">
                    <span>AGENT TARGET LOCK</span>
                    <select
                      value={selectedAgentType}
                      onChange={(e) => setSelectedAgentType(e.target.value)}
                    >
                      <option value="auto">Auto-Route (Task Router)</option>
                      <option value="GeneralAgent">GeneralAgent (General Reasoning)</option>
                      <option value="FileAgent">FileAgent (Filesystem Ops)</option>
                      <option value="SecurityAgent">SecurityAgent (Policy & Threat Guard)</option>
                      <option value="MonitoringAgent">MonitoringAgent (Telemetry & Anomalies)</option>
                      <option value="PlanningAgent">PlanningAgent (Subtask Decomposition)</option>
                      <option value="ImageAgent">ImageAgent (Visual Synthesis & Multimodal)</option>
                    </select>
                  </div>

                  {/* Deadline */}
                  <div className="select-control">
                    <span>DEADLINE (SECONDS)</span>
                    <input
                      type="number"
                      placeholder="Optional deadline in seconds"
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                      min={1}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action Dispatch Buttons */}
          <div className="dispatch-action-row" style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              className="btn-primary-dispatch"
              onClick={handleDispatch}
              disabled={busy || !prompt.trim()}
              title="Dispatch to scheduler and immediately run in background"
            >
              {busy ? (
                <>
                  <span className="spinner-icon" />
                  <span>Scheduling…</span>
                </>
              ) : (
                <>
                  <Send size={15} />
                  <span>Dispatch & Run</span>
                </>
              )}
            </button>

            <button
              type="button"
              className="btn-step"
              style={{
                padding: "10px 16px",
                borderRadius: "8px",
                border: "1px solid rgba(139, 92, 246, 0.5)",
                background: "rgba(139, 92, 246, 0.15)",
                color: "#c084fc",
                fontWeight: "700",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: prompt.trim() ? "pointer" : "not-allowed",
                opacity: prompt.trim() ? 1 : 0.6,
              }}
              onClick={handleEnqueueOnly}
              disabled={!prompt.trim()}
              title="Enqueue task into the scheduler without immediate execution, letting you queue multiple tasks to test FIFO, Priority, or Round Robin ordering"
            >
              <Layers size={14} className="text-violet" />
              <span>Enqueue Only (Hold in Queue)</span>
            </button>

            <button
              type="button"
              className="btn-secondary-instant"
              onClick={handleInstantRun}
              disabled={busy || !prompt.trim()}
              title="Execute immediately without queue delay"
            >
              <Zap size={14} className="text-amber" />
              <span>Instant Run</span>
            </button>

            <button
              type="button"
              className="btn-ghost-clear"
              onClick={() => setPrompt("")}
              disabled={busy || !prompt}
              title="Clear input"
            >
              <RotateCcw size={14} />
            </button>
          </div>
        </section>

        {/* Right Column: Cyber Console & Terminal */}
        <section className="terminal-card glass-panel">
          <div className="terminal-header">
            <div className="terminal-header-title">
              <Terminal size={15} className="text-cyan" />
              <span>AgentOS Cyberdeck Shell</span>
              <span className="stream-badge">
                <Radio size={11} className="pulse-anim" /> LIVE STREAM
              </span>
            </div>
            <div className="terminal-header-actions">
              <button
                className="icon-btn-sm"
                onClick={copyTerminalOutput}
                title="Copy entire terminal output"
              >
                {copiedTerminal ? <Check size={13} className="text-emerald" /> : <Copy size={13} />}
              </button>
              <button
                className="icon-btn-sm"
                onClick={() => setTerminalHistory([])}
                title="Clear screen"
              >
                <RotateCcw size={13} />
              </button>
            </div>
          </div>

          {/* Quick command buttons */}
          <div className="quick-command-bar">
            <span>Commands:</span>
            {["help", "status", "history", "scheduler priority", "step"].map((cmd) => (
              <button
                key={cmd}
                className="terminal-cmd-chip"
                onClick={() => {
                  setTerminalInput(cmd);
                  playCyberClick();
                }}
              >
                {cmd}
              </button>
            ))}
          </div>

          {/* Terminal Screen Body */}
          <div className="terminal-screen">
            {terminalHistory.map((item, idx) => {
              const detectedImg =
                item.imageUrl ||
                item.text?.match(/!\[.*?\]\((.*?)\)/)?.[1] ||
                item.text?.match(/(\/static\/(?:generated|uploads)\/[^\s\)\"']+)/)?.[1];
              return (
                <div key={idx} className={`term-line term-${item.type}`}>
                  <span className="term-timestamp">[{item.time}]</span>
                  <div className="term-content-box">
                    <span className="term-content">{item.text}</span>
                    {detectedImg && (
                      <div className="term-inline-image-card">
                        <div className="term-img-header">
                          <span className="term-img-badge">VISUAL SYNTHESIS ASSET</span>
                          <div className="term-img-actions">
                            <a
                              href={detectedImg}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="term-img-btn"
                              title="Open full resolution in new tab"
                            >
                              <ExternalLink size={12} />
                              <span>Open Full</span>
                            </a>
                            <a
                              href={detectedImg}
                              download
                              className="term-img-btn"
                              title="Download image asset"
                            >
                              <Download size={12} />
                              <span>Download</span>
                            </a>
                          </div>
                        </div>
                        <div className="term-img-wrapper">
                          <img
                            src={detectedImg}
                            alt="Visual Asset"
                            className="term-rendered-img"
                            loading="lazy"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={terminalEndRef} />
          </div>

          {/* Terminal Input Bar */}
          <form className="terminal-input-bar" onSubmit={handleTerminalSubmit}>
            <span className="term-prompt-symbol">agentos@runtime:~$</span>
            <input
              type="text"
              value={terminalInput}
              onChange={(e) => setTerminalInput(e.target.value)}
              placeholder="run <request>, status, scheduler <policy>, help..."
              disabled={busy}
              className="term-input-field"
            />
            <button
              type="submit"
              disabled={busy || !terminalInput.trim()}
              className="term-submit-btn"
            >
              ↵
            </button>
          </form>

          {/* Real-time WebSocket Event Feed Drawer */}
          {events.length > 0 && (
            <div className="live-event-ticker">
              <span className="ticker-label">LATEST EVENT:</span>
              <span className="ticker-msg">
                {events[events.length - 1]?.type?.toUpperCase()}: Task{" "}
                {events[events.length - 1]?.task_id?.slice(0, 8) || ""}{" "}
                {events[events.length - 1]?.status || events[events.length - 1]?.scheduler || ""}
              </span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
