import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [prompt, setPrompt] = useState("");
  const [agentType, setAgentType] = useState("general");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [systemOnline, setSystemOnline] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    checkSystem();
  }, []);

  async function checkSystem() {
    try {
      const result = await fetch(`${API_URL}/`);
      setSystemOnline(result.ok);
    } catch {
      setSystemOnline(false);
    }
  }

  async function runTask() {
    if (!prompt.trim() || loading) {
      return;
    }

    setLoading(true);
    setError("");
    setResponse("");

    const startTime = performance.now();

    try {
      const result = await fetch(`${API_URL}/api/task`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: prompt.trim(),
          agent_type: agentType,
          priority: 5,
          estimated_tokens: 256,
          complexity: 1,
          risk_level: 1,
          required_capabilities: [],
        }),
      });

      const data = await result.json();
      const latency = ((performance.now() - startTime) / 1000).toFixed(2);

      if (!result.ok) {
        throw new Error(
          data.detail
            ? JSON.stringify(data.detail)
            : "AgentOS request failed."
        );
      }

      const taskResponse = data.response || JSON.stringify(data, null, 2);

      setResponse(taskResponse);

      const historyItem = {
        id: data.task?.id || Date.now().toString(),
        prompt: prompt.trim(),
        agent: data.agent || `${agentType} Agent`,
        status: "completed",
        latency: data.latency_seconds
          ? Number(data.latency_seconds).toFixed(2)
          : latency,
        response: taskResponse,
      };

      setHistory((previous) => [historyItem, ...previous]);
    } catch (err) {
      setError(err.message);

      const latency = ((performance.now() - startTime) / 1000).toFixed(2);

      setHistory((previous) => [
        {
          id: Date.now().toString(),
          prompt: prompt.trim(),
          agent: `${agentType} Agent`,
          status: "failed",
          latency,
          response: err.message,
        },
        ...previous,
      ]);
    } finally {
      setLoading(false);
      checkSystem();
    }
  }

  function clearHistory() {
    setHistory([]);
  }

  function selectHistory(item) {
    setPrompt(item.prompt);
    setResponse(item.response);
    setError(item.status === "failed" ? item.response : "");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="brand">AgentOS</div>
          <div className="subtitle">
            Local Multi-Agent AI Operating System
          </div>
        </div>

        <div className="system-status">
          <span className={systemOnline ? "status-dot online" : "status-dot"} />
          {systemOnline ? "System Online" : "System Offline"}
        </div>
      </header>

      <section className="stats">
        <div className="stat-card">
          <span className="stat-label">Agents</span>
          <strong>3</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Tasks</span>
          <strong>{history.length}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Model</span>
          <strong>Qwen 1.5B</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Runtime</span>
          <strong>Local</strong>
        </div>
      </section>

      <main className="dashboard">
        <section className="card task-card">
          <div className="card-header">
            <div>
              <h2>Create Task</h2>
              <p>Send a task to one of your local agents.</p>
            </div>
          </div>

          <label>Agent</label>

          <select
            value={agentType}
            onChange={(event) => setAgentType(event.target.value)}
            disabled={loading}
          >
            <option value="general">General Agent</option>
            <option value="file">File Agent</option>
            <option value="security">Security Agent</option>
          </select>

          <label>Task</label>

          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="What should AgentOS do?"
            disabled={loading}
          />

          <button
            className="run-button"
            onClick={runTask}
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Running..." : "Run Task"}
          </button>
        </section>

        <section className="card response-card">
          <div className="card-header">
            <div>
              <h2>Agent Response</h2>
              <p>Output from the selected agent.</p>
            </div>
          </div>

          {loading && (
            <div className="state-message">
              <div className="loader" />
              AgentOS is processing your task...
            </div>
          )}

          {error && !loading && (
            <div className="error-box">
              <strong>Task failed</strong>
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && !response && (
            <div className="state-message">
              No response yet. Run a task to see the agent output here.
            </div>
          )}

          {response && !loading && (
            <pre className="response-text">{response}</pre>
          )}
        </section>

        <section className="card history-card">
          <div className="card-header">
            <div>
              <h2>Task History</h2>
              <p>Your tasks from this session.</p>
            </div>

            {history.length > 0 && (
              <button className="clear-button" onClick={clearHistory}>
                Clear
              </button>
            )}
          </div>

          {history.length === 0 ? (
            <div className="state-message">
              No tasks have been executed yet.
            </div>
          ) : (
            <div className="history-list">
              {history.map((item) => (
                <button
                  className="history-item"
                  key={item.id}
                  onClick={() => selectHistory(item)}
                >
                  <div className="history-main">
                    <strong>{item.prompt}</strong>

                    <div className="history-meta">
                      <span>{item.agent}</span>
                      <span>{item.latency}s</span>
                    </div>
                  </div>

                  <span
                    className={
                      item.status === "completed"
                        ? "badge success"
                        : "badge failed"
                    }
                  >
                    {item.status}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;