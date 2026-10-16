(() => {
  const $ = (id) => document.getElementById(id);
  // The standalone shell only initializes when its own DOM is present.
  if (!document.getElementById("command")) return;
  const api = async (path, options = {}) => {
    const response = await fetch(path, {headers: {"Content-Type":"application/json"}, ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail?.detail || data.detail || data.error || `Request failed (${response.status})`);
    return data;
  };
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  let busy = false;
  let attachedImageUrl = null;
  let attachedImageFilename = null;

  function setAttachedImage(url, filename) {
    attachedImageUrl = url;
    attachedImageFilename = filename;
    const el = $("imagePreview");
    if (!el) return;
    if (!url) {
      el.className = "hidden";
      el.innerHTML = "";
      return;
    }
    el.className = "";
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;">
        <img src="${url}" style="width:40px;height:40px;object-fit:cover;border-radius:6px;border:1px solid #243653;">
        <div>
          <div style="font-size:12px;font-weight:600;color:#54e6ff;">${escapeHtml(filename || "Attached Image")}</div>
          <div style="font-size:11px;color:#91a2bd;">Ready to submit with task</div>
        </div>
      </div>
      <button type="button" class="voice-stop-btn" id="removeAttachedImageBtn">✕ Remove</button>
    `;
    const rmBtn = $("removeAttachedImageBtn");
    if (rmBtn) rmBtn.onclick = () => setAttachedImage(null, null);
  }

  async function uploadUserImage(file) {
    if (!file) return;
    try {
      showOutput(`Uploading image "${file.name}"...`);
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/upload/image", { method: "POST", body: formData });
      const data = await res.json();
      if (res.ok && data.url) {
        setAttachedImage(data.url, data.filename);
        showOutput(`Image uploaded: ${data.filename} (${data.width}x${data.height}). Ready to submit with your task.`);
      } else {
        showOutput(`Image upload failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      showOutput(`Image upload error: ${err.message}`);
    }
  }

  function showOutput(text) { $("output").textContent = text; }
  function setMetric(id, value, barId) {
    $(id).textContent = value;
    if (barId) $(barId).style.width = `${Math.max(0, Math.min(100, Number.parseFloat(value) || 0))}%`;
  }
  async function refreshMetrics() {
    try {
      const m = await api("/metrics");
      setMetric("cpu", `${m.cpu_percent.toFixed(1)}%`, "cpuBar");
      setMetric("ram", `${m.ram_percent.toFixed(1)}%`, "ramBar");
      setMetric("cpu2", `${m.cpu_percent.toFixed(1)}%`, "cpuBar2");
      setMetric("ram2", `${m.ram_percent.toFixed(1)}%`, "ramBar2");
      $("tokens").textContent = m.tokens_total;
      $("tokens2").textContent = m.tokens_total;
      $("queue").textContent = m.queue_length;
      $("latency").textContent = `${Number(m.latency_seconds).toFixed(2)}s`;
      $("monitorDetails").textContent = JSON.stringify(m, null, 2);
      $("online").textContent = "● RUNTIME ONLINE";
      $("online").style.color = "var(--green)";
    } catch (error) {
      $("online").textContent = "● RUNTIME OFFLINE";
      $("online").style.color = "var(--red)";
    }
  }
  async function refreshHistory() {
    try {
      const data = await api("/history");
      const tasks = [...data.tasks].reverse().slice(0, 12);
      $("history").innerHTML = tasks.length ? tasks.map((task) => `<div class="item"><b>${escapeHtml(task.prompt)}</b><span class="pill">${escapeHtml(task.status)}</span><span class="pill">${escapeHtml(task.agent_type)}</span><span class="pill">P${task.priority}</span><small class="muted"> ${escapeHtml(task.id.slice(0,8))}</small></div>`).join("") : '<div class="empty">No tasks yet.</div>';
    } catch (error) { $("history").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; }
  }
  async function refreshAgents() {
    try {
      const data = await api("/api/agents/status");
      $("agents").innerHTML = data.agents.map((agent) => `<div class="item"><b>${escapeHtml(agent.name)}</b><span class="pill">${escapeHtml(agent.status)}</span><div class="muted">${escapeHtml(agent.model)}</div><small>${escapeHtml((agent.capabilities || []).join(" · "))}</small></div>`).join("");
    } catch (error) { $("agents").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; }
  }
  async function refreshBlocked() {
    try {
      const data = await api("/blocked");
      $("blocked").innerHTML = data.blocked_actions.length ? data.blocked_actions.slice(0,8).map((item) => `<div class="item danger"><b>⛨ ${escapeHtml(item.action || item.tool)}</b><div>${escapeHtml(item.reason)}</div><small>${escapeHtml(item.agent)} · ${escapeHtml(item.timestamp)}</small></div>`).join("") : '<div class="empty">No blocked actions recorded.</div>';
    } catch (error) { $("blocked").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; }
  }
  async function refreshResults() {
    try {
      const data = await api("/api/results/figures");
      const images = (data.figures || []).filter((f) => f.kind !== "pdf");
      const pdfs = (data.figures || []).filter((f) => f.kind === "pdf");
      $("figures").innerHTML = images.length ? images.map((f) => `<div class="figure"><img loading="lazy" src="${f.url}" alt="${escapeHtml(f.title)}"><b>${escapeHtml(f.title)}</b><div style="margin-top:6px;"><a href="${f.url}" target="_blank" rel="noopener">Open Full</a> · <a href="${f.url}" download="${f.name}" style="margin-left:8px;color:var(--green);">Download</a></div></div>`).join("") : '<div class="empty">No figures synthesized yet. Click "⚡ Synthesize Research Figures" above.</div>';
      if (pdfs.length) $("figures").insertAdjacentHTML("beforeend", `<div class="figure full"><b>PDF exports</b><div style="margin-top:8px;">${pdfs.map((f) => `<a style="margin-right:12px;display:inline-block;padding:4px 8px;border:1px solid #243653;border-radius:6px;" href="${f.url}" target="_blank" rel="noopener">📄 ${escapeHtml(f.title)} (.pdf)</a>`).join("")}</div></div>`);
    } catch (error) { $("figures").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; }
  }
  async function pollTask(id) {
    const until = Date.now() + 120000;
    while (Date.now() < until) {
      const item = await api(`/task/${encodeURIComponent(id)}`);
      if (["done","failed","blocked"].includes(item.status)) {
        const result = item.result;
        if (result?.image_url) {
          $("output").innerHTML = `${escapeHtml(item.status.toUpperCase())} · ${escapeHtml(item.agent || "Agent")}\nTask ID: ${escapeHtml(id)}\n\n${escapeHtml(result?.response || result?.error || "Task completed.")}\n\n<div style="margin-top:12px;padding:12px;background:#060d19;border:1px solid #243653;border-radius:10px;"><div style="font-size:11px;color:#54e6ff;font-weight:700;margin-bottom:8px;">SYNTHESIZED / ATTACHED IMAGE ASSET:</div><a href="${result.image_url}" target="_blank"><img src="${result.image_url}" style="max-width:100%;max-height:280px;border-radius:6px;display:block;"></a><div style="margin-top:8px;"><a href="${result.image_url}" target="_blank" style="color:var(--cyan);font-size:12px;text-decoration:none;">↗ Open Full Image</a> · <a href="${result.image_url}" download style="color:var(--green);font-size:12px;text-decoration:none;margin-left:10px;">⬇ Download Image</a></div></div>`;
        } else {
          showOutput(`${item.status.toUpperCase()} · ${item.agent || "Agent"}\nTask ID: ${id}\n\n${result?.response || result?.error || "No response returned."}`);
        }
        await Promise.all([refreshHistory(), refreshMetrics(), refreshBlocked()]);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
    showOutput(`Task ${id} is still running. Use status or check Task History.`);
  }
  async function runCommand() {
    if (busy) return;
    const raw = $("command").value.trim();
    if (!raw) return;
    const first = raw.split(/\s+/, 1)[0].toLowerCase();
    const rest = raw.slice(first.length).trim();
    if (first === "help") { showOutput("Commands:\nrun <request> — submit an AI task\nstatus — runtime health and metrics\nhistory — refresh task history\nscheduler <fifo|priority|roundrobin|resourceaware> — change scheduling policy\nhelp — show commands\n\nAny other text is sent as an AI task. Shell commands are never executed."); return; }
    if (first === "status") { await refreshMetrics(); showOutput(JSON.stringify(await api("/api/status"), null, 2)); return; }
    if (first === "history") { await refreshHistory(); showOutput("Task history refreshed from SQLite."); return; }
    if (first === "scheduler") {
      if (!rest) { showOutput("Usage: scheduler fifo|priority|roundrobin|resourceaware"); return; }
      await switchScheduler(rest); return;
    }
    const prompt = first === "run" ? rest : raw;
    if (!prompt) { showOutput("Usage: run <request>"); return; }
    busy = true; $("run").disabled = true; $("run").textContent = "◌ Running…";
    showOutput("Submitting task to AgentOS scheduler…");
    try {
      const payload = {
        prompt,
        image_url: attachedImageUrl,
        priority: 5,
        estimated_tokens: 256,
        complexity: 1,
        risk_level: 1
      };
      const submitted = await api("/task", {method:"POST", body:JSON.stringify(payload)});
      showOutput(`QUEUED · ${submitted.agent}\nTask ID: ${submitted.task_id}\nScheduler: ${submitted.scheduler}\nWaiting for agent response…`);
      await pollTask(submitted.task_id);
      setAttachedImage(null, null);
    } catch (error) { showOutput(`Request error: ${error.message}`); }
    finally { busy = false; $("run").disabled = false; $("run").textContent = "▶ Execute"; }
  }
  async function switchScheduler(value) {
    const scheduler = value.trim().toLowerCase();
    try {
      const data = await api("/scheduler", {method:"POST", body:JSON.stringify({scheduler})});
      $("scheduler").value = scheduler;
      $("schedulerName").textContent = `${data.scheduler} scheduler`;
      showOutput(`Scheduler switched to ${data.scheduler}.`);
    } catch (error) {
      showOutput(`Scheduler error: ${error.message}`);
    }
  }
  // --- Voice Input (Web Speech API) ---
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;
  let previousPrompt = "";

  function setVoiceStatus(message, state = "info", actionBtn = null) {
    const el = $("voiceStatus");
    if (!el) return;
    if (!message) {
      el.className = "voice-status-bar hidden";
      el.innerHTML = "";
      return;
    }
    el.className = `voice-status-bar ${state}`;
    el.innerHTML = `<span>${escapeHtml(message)}</span>`;
    if (actionBtn) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "voice-stop-btn";
      btn.textContent = actionBtn.text;
      btn.onclick = actionBtn.onClick;
      el.appendChild(btn);
    }
  }

  function stopVoiceInput() {
    if (recognition && isListening) {
      try { recognition.stop(); } catch (_) {}
    }
    isListening = false;
    const btn = $("voiceBtn");
    if (btn) {
      btn.classList.remove("listening");
      const icon = $("voiceIcon");
      const text = $("voiceText");
      if (icon) icon.textContent = "🎙";
      if (text) text.textContent = "Voice Input";
    }
  }

  function initVoiceInput() {
    const btn = $("voiceBtn");
    if (!btn) return;
    if (!SpeechRecognition) {
      btn.classList.add("unsupported");
      btn.title = "Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.";
      const badge = $("voiceBadge");
      if (badge) {
        badge.textContent = "Voice: Unsupported";
        badge.style.borderColor = "#71334a";
        badge.style.color = "#ff9db0";
      }
      btn.addEventListener("click", () => {
        setVoiceStatus("Web Speech API is not supported in this browser. You can still type and execute tasks normally.", "error");
      });
      return;
    }

    btn.addEventListener("click", () => {
      if (isListening) {
        stopVoiceInput();
        setVoiceStatus("Voice input stopped. Review or edit your transcription, then click ▶ Execute.", "success");
        return;
      }
      try {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = navigator.language || "en-US";
        recognition.maxAlternatives = 1;

        previousPrompt = $("command").value ? $("command").value.trim() + " " : "";

        recognition.onstart = () => {
          isListening = true;
          btn.classList.add("listening");
          const icon = $("voiceIcon");
          const text = $("voiceText");
          if (icon) icon.textContent = "⏹";
          if (text) text.textContent = "Stop Listening";
          setVoiceStatus("Listening... Speak your task now", "listening", {
            text: "Stop Listening",
            onClick: () => {
              stopVoiceInput();
              setVoiceStatus("Voice input stopped. Review or edit transcription, then click ▶ Execute.", "success");
            }
          });
        };

        recognition.onresult = (event) => {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = 0; i < event.results.length; ++i) {
            const piece = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += piece;
            } else {
              interimTranscript += piece;
            }
          }

          const combined = (previousPrompt + finalTranscript + (interimTranscript ? " " + interimTranscript : "")).trim();
          $("command").value = combined;

          if (interimTranscript) {
            setVoiceStatus(`Transcribing: "${interimTranscript}"`, "listening", {
              text: "Done",
              onClick: () => stopVoiceInput()
            });
          } else if (finalTranscript) {
            setVoiceStatus("Transcription captured. Review/edit the text above, then click ▶ Execute.", "success");
          }
        };

        recognition.onerror = (event) => {
          stopVoiceInput();
          if (event.error === "not-allowed") {
            setVoiceStatus("Microphone permission denied. Please allow microphone access in your browser settings.", "error");
          } else if (event.error === "no-speech") {
            setVoiceStatus("No speech detected. Click Voice Input to try again.", "info");
          } else if (event.error === "network") {
            setVoiceStatus("Speech recognition service network issue. Normal typed task submission is ready.", "error");
          } else {
            setVoiceStatus(`Speech recognition error: ${event.error}. You can type and execute normally.`, "error");
          }
        };

        recognition.onend = () => {
          stopVoiceInput();
          if ($("command").value.trim().length > 0) {
            setVoiceStatus("Transcription ready for review. Edit if needed, then click ▶ Execute.", "success");
          }
        };

        recognition.start();
      } catch (err) {
        stopVoiceInput();
        setVoiceStatus(`Could not start speech recognition: ${err.message}`, "error");
      }
    });
  }

  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("active", item === button));
    ["shell","monitor","results"].forEach((name) => $(name).classList.toggle("hidden", name !== button.dataset.tab));
    if (button.dataset.tab === "results") refreshResults();
    if (button.dataset.tab === "monitor") refreshMetrics();
  }));
  $("run").addEventListener("click", runCommand);
  $("command").addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runCommand(); });
  $("help").addEventListener("click", () => { $("command").value = "help"; runCommand(); });
  $("switch").addEventListener("click", () => switchScheduler($("scheduler").value));
  $("refreshResults").addEventListener("click", refreshResults);

  const imgInput = $("imageInput");
  if (imgInput) {
    imgInput.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) uploadUserImage(file);
      e.target.value = "";
    });
  }

  const genFiguresBtn = $("genFiguresBtn");
  if (genFiguresBtn) {
    genFiguresBtn.addEventListener("click", async () => {
      try {
        const stat = $("figureStatus");
        if (stat) stat.textContent = "Synthesizing research figures with Matplotlib engine...";
        genFiguresBtn.disabled = true;
        const res = await api("/api/figures/generate", { method: "POST" });
        if (stat) stat.textContent = `Generated ${res.count || 6} research benchmark figures!`;
        await refreshResults();
      } catch (err) {
        const stat = $("figureStatus");
        if (stat) stat.textContent = `Generation error: ${err.message}`;
      } finally {
        genFiguresBtn.disabled = false;
      }
    });
  }

  const figUploadInput = $("figureUploadInput");
  if (figUploadInput) {
    figUploadInput.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const stat = $("figureStatus");
        if (stat) stat.textContent = `Uploading figure "${file.name}"...`;
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/api/figures/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (res.ok && data.status === "ok") {
          if (stat) stat.textContent = `Figure "${data.filename}" uploaded successfully!`;
          await refreshResults();
        } else {
          if (stat) stat.textContent = `Upload failed: ${data.detail || "Error"}`;
        }
      } catch (err) {
        const stat = $("figureStatus");
        if (stat) stat.textContent = `Upload error: ${err.message}`;
      } finally {
        e.target.value = "";
      }
    });
  }

  initVoiceInput();
  refreshMetrics(); refreshHistory(); refreshAgents(); refreshBlocked();
  setInterval(() => { refreshMetrics(); refreshHistory(); refreshBlocked(); }, 3000);
  try {
    const socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/stream`);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "blocked_action") refreshBlocked();
      if (data.type === "task_updated") { refreshHistory(); refreshMetrics(); }
    };
  } catch (_) { /* polling remains available if WebSocket is unavailable */ }
})();
