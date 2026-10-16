/**
 * AgentOS Voice Input Module (Web Speech API)
 *
 * Integrates native browser speech recognition into the AgentOS dashboard.
 * Supports Chrome, Edge, Safari, and other Web Speech API compliant browsers.
 * Transcribes spoken speech into the task prompt field, allowing review and editing
 * before manual dispatch through the existing /api/task or /task endpoints.
 */
(() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  let recognition = null;
  let isListening = false;
  let activeTextarea = null;
  let previousText = "";

  // Inject voice input stylesheet
  function injectStyles() {
    if (document.getElementById("agentos-voice-styles")) return;
    const style = document.createElement("style");
    style.id = "agentos-voice-styles";
    style.textContent = `
      .voice-input-container {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-top: 6px;
        font-family: inherit;
      }
      .voice-input-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        flex-wrap: wrap;
      }
      .btn-voice-mic {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 7px 14px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid rgba(84, 230, 255, 0.35);
        background: linear-gradient(135deg, rgba(14, 35, 56, 0.9), rgba(22, 43, 71, 0.9));
        color: #54e6ff;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
      }
      .btn-voice-mic:hover {
        border-color: #54e6ff;
        box-shadow: 0 0 16px rgba(84, 230, 255, 0.35);
        color: #ffffff;
      }
      .btn-voice-mic.listening {
        border-color: #ff5577;
        background: linear-gradient(135deg, rgba(61, 14, 28, 0.95), rgba(102, 24, 47, 0.95));
        color: #ffffff;
        animation: pulseMicAura 1.4s infinite;
      }
      .btn-voice-mic.unsupported {
        opacity: 0.55;
        cursor: not-allowed;
        border-color: rgba(145, 162, 189, 0.3);
        color: #91a2bd;
      }
      @keyframes pulseMicAura {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 85, 119, 0.5); }
        50% { box-shadow: 0 0 0 8px rgba(255, 85, 119, 0); }
      }
      .voice-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        border: 1px solid rgba(36, 54, 83, 0.9);
        background: rgba(9, 20, 36, 0.95);
        color: #b5c8e4;
      }
      .voice-status-pill.listening {
        border-color: #ff5577;
        color: #ff9db0;
        background: rgba(30, 10, 18, 0.95);
      }
      .voice-status-pill.success {
        border-color: #4cdae9;
        color: #54e6ff;
      }
      .voice-status-pill.error {
        border-color: #ff6d8b;
        color: #ff6d8b;
        background: rgba(35, 10, 18, 0.95);
      }
      .voice-action-btn {
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid rgba(255, 109, 139, 0.5);
        background: rgba(60, 15, 25, 0.8);
        color: #ff9db0;
        margin-left: 6px;
      }
      .voice-hint-badge {
        font-size: 11px;
        color: #64748b;
        margin-left: auto;
      }
    `;
    document.head.appendChild(style);
  }

  // Update textarea and trigger React/DOM synthetic events
  function setInputValue(textarea, value) {
    if (!textarea) return;
    try {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      if (nativeSetter) {
        nativeSetter.call(textarea, value);
      } else {
        textarea.value = value;
      }
    } catch (_) {
      textarea.value = value;
    }
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    textarea.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Render status message
  function updateStatus(statusEl, message, state = "info", action = null) {
    if (!statusEl) return;
    if (!message) {
      statusEl.style.display = "none";
      statusEl.innerHTML = "";
      return;
    }
    statusEl.style.display = "inline-flex";
    statusEl.className = `voice-status-pill ${state}`;
    statusEl.innerHTML = `<span>${escapeText(message)}</span>`;
    if (action) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "voice-action-btn";
      btn.textContent = action.label;
      btn.onclick = action.onClick;
      statusEl.appendChild(btn);
    }
  }

  function escapeText(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  }

  function stopListening(micBtn, statusEl) {
    if (recognition && isListening) {
      try { recognition.stop(); } catch (_) {}
    }
    isListening = false;
    if (micBtn) {
      micBtn.classList.remove("listening");
      micBtn.innerHTML = `<span>🎙</span> <span>Voice Input</span>`;
      micBtn.title = "Start voice input (Speech-to-Text)";
      micBtn.setAttribute("aria-label", "Start voice input");
    }
  }

  // Bind to textarea (either #task-prompt in React or #command in fallback shell)
  function attachVoiceInput(textarea) {
    if (textarea.dataset.voiceAttached === "true") return;
    textarea.dataset.voiceAttached = "true";

    injectStyles();

    const parent = textarea.closest(".prompt-input-wrapper") || textarea.parentElement;
    if (!parent) return;

    // Create voice controls wrapper
    const container = document.createElement("div");
    container.className = "voice-input-container";

    const bar = document.createElement("div");
    bar.className = "voice-input-bar";

    const micBtn = document.createElement("button");
    micBtn.type = "button";
    micBtn.className = "btn-voice-mic";
    micBtn.id = "agentos-mic-btn";
    micBtn.setAttribute("aria-label", "Start voice input");
    micBtn.innerHTML = `<span>🎙</span> <span>Voice Input</span>`;

    const statusEl = document.createElement("div");
    statusEl.className = "voice-status-pill";
    statusEl.style.display = "none";
    statusEl.setAttribute("aria-live", "polite");

    const hint = document.createElement("span");
    hint.className = "voice-hint-badge";
    hint.textContent = SpeechRecognition ? "Web Speech API ready" : "Speech API unsupported in browser";

    bar.appendChild(micBtn);
    bar.appendChild(statusEl);
    bar.appendChild(hint);
    container.appendChild(bar);

    // Insert after textarea
    if (textarea.nextSibling) {
      parent.insertBefore(container, textarea.nextSibling);
    } else {
      parent.appendChild(container);
    }

    if (!SpeechRecognition) {
      micBtn.classList.add("unsupported");
      micBtn.title = "Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.";
      micBtn.onclick = () => {
        updateStatus(statusEl, "Web Speech API is unsupported in this browser. Please type your task prompt.", "error");
      };
      return;
    }

    micBtn.onclick = (e) => {
      e.preventDefault();
      activeTextarea = textarea;

      if (isListening) {
        stopListening(micBtn, statusEl);
        updateStatus(statusEl, "Voice input stopped. Review or edit the text above, then dispatch.", "success");
        return;
      }

      try {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = navigator.language || "en-US";
        recognition.maxAlternatives = 1;

        previousText = textarea.value ? textarea.value.trim() + " " : "";

        recognition.onstart = () => {
          isListening = true;
          micBtn.classList.add("listening");
          micBtn.innerHTML = `<span>⏹</span> <span>Stop Listening</span>`;
          micBtn.title = "Stop listening and review transcription";
          micBtn.setAttribute("aria-label", "Stop listening");
          updateStatus(statusEl, "Listening... Speak your task clearly", "listening", {
            label: "Stop",
            onClick: () => {
              stopListening(micBtn, statusEl);
              updateStatus(statusEl, "Voice captured. Review or edit, then dispatch.", "success");
            }
          });
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

          const combined = (previousText + final + (interim ? " " + interim : "")).trim();
          setInputValue(textarea, combined);

          if (interim) {
            updateStatus(statusEl, `Transcribing: "${interim}"`, "listening", {
              label: "Done",
              onClick: () => {
                stopListening(micBtn, statusEl);
                updateStatus(statusEl, "Voice input ready for review. Click Dispatch to submit.", "success");
              }
            });
          } else if (final) {
            updateStatus(statusEl, "Transcription captured. Edit if needed, then dispatch.", "success");
          }
        };

        recognition.onerror = (event) => {
          console.warn("[AgentOS Voice] Speech error:", event.error);
          stopListening(micBtn, statusEl);
          if (event.error === "not-allowed") {
            updateStatus(statusEl, "Microphone permission denied. Allow microphone access in browser settings.", "error");
          } else if (event.error === "no-speech") {
            updateStatus(statusEl, "No speech detected. Click Voice Input to try again.", "info");
          } else if (event.error === "network") {
            updateStatus(statusEl, "Speech service network error. Ensure internet connection for speech engine.", "error");
          } else {
            updateStatus(statusEl, `Speech error: ${event.error}`, "error");
          }
        };

        recognition.onend = () => {
          stopListening(micBtn, statusEl);
          if (textarea.value.trim().length > 0) {
            updateStatus(statusEl, "Transcription ready. Review and click Dispatch to Scheduler or Instant Run.", "success");
          }
        };

        recognition.start();
      } catch (err) {
        stopListening(micBtn, statusEl);
        updateStatus(statusEl, `Could not start speech recognition: ${err.message}`, "error");
      }
    };
  }

  // Periodic and MutationObserver scanner for task input fields
  function scanAndAttach() {
    const promptTextarea = document.getElementById("task-prompt") || document.getElementById("command");
    if (promptTextarea) {
      attachVoiceInput(promptTextarea);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      scanAndAttach();
      setInterval(scanAndAttach, 1000);
    });
  } else {
    scanAndAttach();
    setInterval(scanAndAttach, 1000);
  }

  const observer = new MutationObserver(() => scanAndAttach());
  observer.observe(document.body, { childList: true, subtree: true });
})();
