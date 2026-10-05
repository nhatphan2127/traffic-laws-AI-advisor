# =============================================================================
# Backend API: auth, chat history (MongoDB) and RAG chat over SSE.
# Talks to the retrieval service over MCP (RETRIEVAL_MCP_URL).
#
#   docker build -t traffic-law-backend ./backend
#   docker run -p 8000:8000 --env-file backend/.env traffic-law-backend
# =============================================================================

# Slim image: the backend only needs pure-Python / prebuilt-wheel dependencies.
FROM python:3.12-slim

# - no .pyc files, unbuffered logs (shown immediately by `docker logs`)
# - no pip cache / version check, to keep the image small and the build quiet
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code (see .dockerignore: .env, logs and tests are not copied;
# secrets are injected at runtime with --env-file / compose `env_file`).
COPY . .

# Run as an unprivileged user; it owns /app so it can write logs/.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

# Liveness check used by `docker ps` and compose `depends_on: condition: service_healthy`.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
