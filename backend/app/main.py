"""Backend API: auth, chat history and the RAG chat endpoint (SSE).

Run from the backend folder:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging_setup import setup_logging

setup_logging()

from app.api.routes import auth, chat, chats  # noqa: E402
from app.services.chat_engine import ChatEngine  # noqa: E402

logger = logging.getLogger("server")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.engine = ChatEngine()
        logger.info("ChatEngine initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize ChatEngine: {e}", exc_info=True)
        raise
    yield


app = FastAPI(title="Vietnamese Traffic Law RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(chat.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI application via Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
