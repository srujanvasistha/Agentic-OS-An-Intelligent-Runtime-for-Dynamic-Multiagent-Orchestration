#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:1.5b}"
export AGENTOS_LLM_BACKEND="${AGENTOS_LLM_BACKEND:-ollama}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

if [[ "$AGENTOS_LLM_BACKEND" == "ollama" ]]; then
  if ! curl -fsS "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; then
    if command -v ollama >/dev/null 2>&1 && [[ "$OLLAMA_BASE_URL" == "http://127.0.0.1:11434" ]]; then
      echo "Starting local Ollama service…"
      nohup ollama serve > "$ROOT/ollama.log" 2>&1 &
      for _ in $(seq 1 40); do
        curl -fsS "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1 && break
        sleep 0.5
      done
    fi
  fi
  if ! curl -fsS "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; then
    echo "Ollama is not reachable at $OLLAMA_BASE_URL. Start it or use AGENTOS_LLM_BACKEND=mock for an offline smoke test." >&2
    exit 2
  fi
  if ! curl -fsS "$OLLAMA_BASE_URL/api/tags" | grep -q "$OLLAMA_MODEL"; then
    echo "Model $OLLAMA_MODEL is not installed locally. Prepare it before offline demo." >&2
    exit 2
  fi
fi

"$PYTHON_BIN" -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 0.5
done
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "AgentOS backend failed to start. Check backend logs above." >&2
  exit 1
fi
URL="http://127.0.0.1:8000"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true
fi
echo "AgentOS is running at $URL (Ctrl+C to stop)."
wait "$SERVER_PID"
