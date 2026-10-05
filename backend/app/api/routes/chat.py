import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user_optional
from app.db.mongo import chats_collection
from app.services.chat_engine import ChatEngine

logger = logging.getLogger("server")

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    history: List[Dict[str, str]] = []


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _save_history(message: str, final_answer: str, chat_id: Optional[str], user_id: str) -> Optional[dict]:
    """Persist the turn; returns the new-chat event payload when a thread was created."""
    chats = chats_collection()
    user_msg = {"role": "user", "content": message, "timestamp": datetime.now(UTC).isoformat()}
    bot_msg = {"role": "assistant", "content": final_answer, "timestamp": datetime.now(UTC).isoformat()}

    if chat_id:
        try:
            update_result = chats.update_one(
                {"_id": ObjectId(chat_id), "user_id": user_id},
                {
                    "$push": {"messages": {"$each": [user_msg, bot_msg]}},
                    "$set": {"updated_at": datetime.now(UTC)}
                }
            )
            if update_result.matched_count == 0:
                logger.warning(f"Could not update chat history. Chat ID '{chat_id}' not found for user '{user_id}'")
        except InvalidId:
            logger.warning(f"Failed to update chat history. Invalid chat_id format '{chat_id}'")
        return None

    # Create a new conversation thread
    title = message[:30] + "..." if len(message) > 30 else message
    new_chat = {
        "user_id": user_id,
        "title": title,
        "messages": [user_msg, bot_msg],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    res = chats.insert_one(new_chat)
    logger.info(f"Created new chat thread '{res.inserted_id}' for user '{user_id}'")
    return {"new_chat_id": str(res.inserted_id), "title": title}


async def chat_generator(
    engine: ChatEngine, message: str, history: List[Dict[str, str]], chat_id: Optional[str], user_id: Optional[str]
):
    final_answer = ""

    try:
        # 1. Stream responses from LLM Chat Engine
        async for docs, answer, thinking in engine.chat(message, history):
            if answer:
                final_answer += answer
            yield _sse({"docs": docs, "answer": answer, "thinking": thinking, "chat_id": chat_id})

    except Exception as e:
        logger.error(f"Error during LLM streaming response: {e}", exc_info=True)
        # Gracefully emit error payload to client via SSE stream instead of breaking connection
        yield _sse({"error": "An error occurred while generating the AI response."})
        return

    # 2. Persist message history to Database upon stream completion
    if user_id:
        try:
            new_chat_event = await asyncio.to_thread(_save_history, message, final_answer, chat_id, user_id)
            if new_chat_event:
                # Emit newly generated chat_id back to client
                yield _sse(new_chat_event)
        except Exception as e:
            # DB save failure shouldn't crash an already completed stream, just log it
            logger.error(f"Failed to save chat history to database: {e}", exc_info=True)


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest, http_request: Request, user_id: Optional[str] = Depends(get_current_user_optional)
):
    logger.info(f"Chat request received. User ID: '{user_id}', Chat ID: '{request.chat_id}'")
    engine: ChatEngine = http_request.app.state.engine
    return StreamingResponse(
        chat_generator(engine, request.message, request.history, request.chat_id, user_id),
        media_type="text/event-stream"
    )
