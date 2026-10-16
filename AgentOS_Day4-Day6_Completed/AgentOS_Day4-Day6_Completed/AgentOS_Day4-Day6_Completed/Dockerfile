# Linux backend image. Build with a pre-populated wheelhouse for offline dependency installation.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AGENTOS_LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:1.5b OLLAMA_BASE_URL=http://ollama:11434
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends bubblewrap curl libcap2-bin \
    && rm -rf /var/lib/apt/lists/*
COPY wheelhouse/ /wheelhouse/
COPY requirements.txt /app/requirements.txt
RUN if find /wheelhouse -type f -name '*.whl' -print -quit | grep -q .; then \
      python -m pip install --no-index --find-links /wheelhouse -r /app/requirements.txt; \
    else \
      echo "No local wheels found; using package index during image build (pre-populate wheelhouse for offline builds)." && \
      python -m pip install -r /app/requirements.txt; \
    fi
COPY backend/ /app/backend/
COPY experiments/ /app/experiments/
COPY results/ /app/results/
COPY frontend/ /app/frontend/
COPY scripts/ /app/scripts/
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
