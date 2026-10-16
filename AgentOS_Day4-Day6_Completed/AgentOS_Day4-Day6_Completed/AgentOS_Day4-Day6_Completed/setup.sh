#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "AgentOS runtime sandbox requires Linux (use WSL2 or Docker on Windows)." >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
WHEELHOUSE="${WHEELHOUSE:-$ROOT/wheelhouse}"
if [[ ! -d "$WHEELHOUSE" ]]; then
  echo "Missing local wheelhouse: $WHEELHOUSE" >&2
  echo "Populate wheelhouse/ with all requirements.txt wheels before offline setup." >&2
  exit 2
fi
if ! find "$WHEELHOUSE" -type f -name '*.whl' -print -quit | grep -q .; then
  echo "No Python wheels found in $WHEELHOUSE. Offline setup cannot install dependencies yet." >&2
  echo "On a matching online machine, run: python -m pip download -r requirements.txt -d wheelhouse" >&2
  exit 2
fi

"$PYTHON_BIN" -m venv .venv
# Do not access package indexes: this is intentionally offline-only.
.venv/bin/python -m pip install --no-index --find-links "$WHEELHOUSE" -r requirements.txt

# Install bubblewrap from local OS package cache or a pre-downloaded .deb.
if ! command -v bwrap >/dev/null 2>&1; then
  BWRAP_DEB="$(find "$ROOT/installers" -maxdepth 1 -type f -name 'bubblewrap*.deb' -print -quit 2>/dev/null || true)"
  if [[ -n "$BWRAP_DEB" ]]; then
    sudo dpkg -i "$BWRAP_DEB"
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install --no-download -y bubblewrap || {
      echo "bubblewrap package is not in the local apt cache. Add installers/bubblewrap*.deb first." >&2
      exit 2
    }
  else
    echo "bubblewrap is missing. Add a local installer under installers/." >&2
    exit 2
  fi
fi

# Install Ollama from a pre-downloaded Linux tarball when it is not already installed.
if ! command -v ollama >/dev/null 2>&1; then
  OLLAMA_TARBALL="$(find "$ROOT/installers" -maxdepth 1 -type f -name 'ollama-linux-*.tar.zst' -print -quit 2>/dev/null || true)"
  if [[ -n "$OLLAMA_TARBALL" ]]; then
    sudo tar --zstd -xf "$OLLAMA_TARBALL" -C /usr
  else
    echo "Ollama is missing. Add a pre-downloaded Ollama Linux tarball under installers/." >&2
    exit 2
  fi
fi

# Start the local daemon so model inspection/import commands can talk to it.
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required by setup.sh; install it from your local OS package cache." >&2
  exit 2
fi
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup ollama serve > "$ROOT/ollama-setup.log" 2>&1 &
  for _ in $(seq 1 40); do
    curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
  done
fi
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama daemon did not start. Check ollama-setup.log." >&2
  exit 2
fi

# If the model store is not pre-populated, import a local GGUF model.
if ! ollama list 2>/dev/null | grep -q 'qwen2.5:1.5b'; then
  MODEL_FILE="$ROOT/models/qwen2.5-1.5b.gguf"
  if [[ -f "$MODEL_FILE" ]]; then
    MODELFILE_TMP="$(mktemp)"
    printf 'FROM %s\\n' "$MODEL_FILE" > "$MODELFILE_TMP"
    ollama create qwen2.5:1.5b -f "$MODELFILE_TMP"
    rm -f "$MODELFILE_TMP"
  else
    echo "The Qwen model is not installed. Add models/qwen2.5-1.5b.gguf or pre-populate the Ollama model store before going offline." >&2
    exit 2
  fi
fi

echo "Setup checks passed. To build the web UI, run: cd frontend && npm ci && npm run build"
echo "For a completely offline frontend build, pre-cache npm packages or provide a local npm cache as well."
