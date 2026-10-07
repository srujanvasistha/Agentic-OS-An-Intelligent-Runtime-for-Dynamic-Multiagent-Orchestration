import time
import requests

URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:1.5b"

print("Testing Ollama...")
print("Model:", MODEL)

try:
    start = time.time()
    response = requests.post(URL, json={
        "model": MODEL,
        "prompt": "Explain what an AI agent is in one sentence.",
        "stream": False,
    }, timeout=120)
    elapsed = time.time() - start
    print("HTTP Status:", response.status_code)
    response.raise_for_status()
    data = response.json()
    print("\nModel response:")
    print(data.get("response", ""))
    print("\nTotal time:", round(elapsed, 2), "seconds")
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 0)
    if eval_count and eval_duration:
        print("Tokens generated:", eval_count)
        print("Tokens/sec:", round(eval_count / (eval_duration / 1_000_000_000), 2))
    else:
        print("Tokens/sec: unavailable")
except requests.exceptions.ConnectionError:
    print("ERROR: Ollama is not running.")
except Exception as exc:
    print("ERROR:", exc)
