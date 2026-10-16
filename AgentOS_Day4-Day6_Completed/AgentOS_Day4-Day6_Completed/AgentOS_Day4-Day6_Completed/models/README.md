# Offline model preparation

Either pre-populate the Ollama model store with `qwen2.5:1.5b` before going offline, or place a compatible Qwen2.5-1.5B GGUF file at `models/qwen2.5-1.5b.gguf`. If using the GGUF path, `setup.sh` imports that local model into Ollama under the tag `qwen2.5:1.5b`. The model weights are not included in this repository archive.
