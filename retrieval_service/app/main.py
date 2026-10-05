"""Retrieval service: MCP (Streamable HTTP) under /mcp, plus /api/health for liveness checks.

Run from the retrieval_service folder:
    uvicorn app.main:app --host 0.0.0.0 --port 5555
"""
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging_setup import setup_logging

setup_logging()

from app.mcp_server.server import mcp, streamable_http_app  # noqa: E402

logger = logging.getLogger("retrieval_api")

mcp_app = streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        logger.info("MCP server ready at /mcp")
        yield


app = FastAPI(
    title="Hybrid Retrieval & Legal Clause Filter Service",
    description="Hybrid Search (RRF + Reranking) and Qdrant clause/point filtering, exposed as MCP tools (/mcp).",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)



@app.get("/api/health")
def health_check():
    """Liveness check for Docker / monitoring (does not touch Qdrant or the model)."""
    return {"status": "ok"}


# Mounted last so /api/health takes precedence; serves /mcp.
app.mount("/", mcp_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5555)
