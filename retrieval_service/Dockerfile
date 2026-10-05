# =============================================================================
# Retrieval service: hybrid search over the legal corpus.
#   MCP       -> http://<host>:5555/mcp   (Streamable HTTP, used by the backend)
#   Health    -> http://<host>:5555/api/health
#
#   docker build -t traffic-law-retrieval ./retrieval_service
#   docker run -p 5555:5555 --env-file retrieval_service/.env \
#              -e DB_URL=http://<qdrant-host>:6333 traffic-law-retrieval
# =============================================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Hugging Face cache (embedding / reranker models). Mount a volume here so
    # the ~2 GB model is downloaded once, not on every container start.
    HF_HOME=/models/huggingface

WORKDIR /app

# CPU-only PyTorch: the default PyPI wheel bundles CUDA (~3 GB of extra layers)
# that this service does not use. Installed before requirements.txt so that
# sentence-transformers reuses it instead of pulling the CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Code, config, processed data and the BM25 model (artifacts/bm25store.pkl).
# Raw/WIP data, evaluation, scripts, tests and Qdrant snapshots are excluded
# by .dockerignore; secrets come from --env-file / compose `env_file`.
COPY . .

# Unprivileged user. It owns /app (logs/) and the model cache directory, so a
# fresh named volume mounted at $HF_HOME inherits this ownership.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p "$HF_HOME" \
    && chown -R app:app /app /models
USER app

EXPOSE 5555

# Liveness check (does not touch Qdrant or the model).
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5555/api/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5555"]
