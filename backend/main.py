import json
import asyncio
import logging
from datetime import datetime, UTC
from typing import List, Dict, Optional
from dataclasses import asdict

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId

# Project-specific imports
from backend.database import users_collection, chats_collection
from backend.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user, 
    get_current_user_optional
)
from llm.chat_engine import ChatEngine

logger = logging.getLogger("backend")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Chat Engine with startup safety
try:
    engine = ChatEngine()
    logger.info("ChatEngine initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize ChatEngine: {e}", exc_info=True)
    raise e

# --- Auth Models & Routes ---
class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(req: AuthRequest):
    logger.info(f"Registration attempt for username: '{req.username}'")
    try:
        if users_collection.find_one({"username": req.username}):
            logger.warning(f"Registration failed: Username '{req.username}' already exists.")
            raise HTTPException(status_code=400, detail="Username already exists")
        
        hashed = hash_password(req.password)
        user_doc = {
            "username": req.username,
            "password": hashed,
            "created_at": datetime.now(UTC)
        }
        result = users_collection.insert_one(user_doc)
        token = create_access_token({"sub": str(result.inserted_id), "username": req.username})
        
        logger.info(f"User '{req.username}' registered successfully with ID: {result.inserted_id}")
        return {"token": token, "username": req.username}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration for '{req.username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@app.post("/api/login")
def login(req: AuthRequest):
    logger.info(f"Login attempt for username: '{req.username}'")
    try:
        user = users_collection.find_one({"username": req.username})
        if not user or not verify_password(req.password, user["password"]):
            logger.warning(f"Login failed: Invalid credentials for username '{req.username}'")
            raise HTTPException(status_code=400, detail="Invalid username or password")
        
        token = create_access_token({"sub": str(user["_id"]), "username": user["username"]})
        logger.info(f"User '{req.username}' logged in successfully.")
        return {"token": token, "username": user["username"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login for '{req.username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login")

# --- History Routes ---
@app.get("/api/chats")
def get_user_chats(user_id: str = Depends(get_current_user)):
    try:
        chats = list(chats_collection.find({"user_id": user_id}).sort("updated_at", -1))
        return [
            {
                "id": str(c["_id"]),
                "title": c.get("title", "New Conversation"),
                "updated_at": c.get("updated_at").isoformat() if c.get("updated_at") else ""
            }
            for c in chats
        ]
    except Exception as e:
        logger.error(f"Error fetching chats for user_id '{user_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")

@app.get("/api/chats/{chat_id}")
def get_chat_detail(chat_id: str, user_id: str = Depends(get_current_user)):
    try:
        # Catch invalid ObjectId string formats (e.g. invalid 24-hex string)
        obj_id = ObjectId(chat_id)
    except InvalidId:
        logger.warning(f"Invalid ObjectId format provided: '{chat_id}'")
        raise HTTPException(status_code=400, detail="Invalid chat ID format")

    try:
        chat = chats_collection.find_one({"_id": obj_id, "user_id": user_id})
        if not chat:
            logger.warning(f"Chat not found for chat_id '{chat_id}' and user_id '{user_id}'")
            raise HTTPException(status_code=404, detail="Chat conversation not found")
        
        return {
            "id": str(chat["_id"]),
            "title": chat.get("title", "Conversation"),
            "messages": chat.get("messages", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat detail for chat_id '{chat_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error retrieving chat details")

# --- Chat Stream Route ---
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    history: List[Dict[str, str]] = []

async def chat_generator(message: str, history: List[Dict[str, str]], chat_id: Optional[str], user_id: Optional[str]):
    final_answer = ""
    
    try:
        # 1. Stream responses from LLM Chat Engine
        for docs, answer, thinking in engine.chat(message, history):
            docs_to_send = [asdict(d) if hasattr(d, '__dataclass_fields__') else d for d in docs]
            if answer:
                final_answer += answer
                
            data = {
                "docs": docs_to_send,
                "answer": answer,
                "thinking": thinking,
                "chat_id": chat_id
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"Error during LLM streaming response: {e}", exc_info=True)
        # Gracefully emit error payload to client via SSE stream instead of breaking connection
        error_payload = {"error": "An error occurred while generating the AI response."}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        return

    # 2. Persist message history to Database upon stream completion
    if user_id:
        try:
            user_msg = {"role": "user", "content": message, "timestamp": datetime.now(UTC).isoformat()}
            bot_msg = {"role": "assistant", "content": final_answer, "timestamp": datetime.now(UTC).isoformat()}

            if chat_id:
                try:
                    obj_id = ObjectId(chat_id)
                    update_result = chats_collection.update_one(
                        {"_id": obj_id, "user_id": user_id},
                        {
                            "$push": {"messages": {"$each": [user_msg, bot_msg]}},
                            "$set": {"updated_at": datetime.now(UTC)}
                        }
                    )
                    if update_result.matched_count == 0:
                        logger.warning(f"Could not update chat history. Chat ID '{chat_id}' not found for user '{user_id}'")
                except InvalidId:
                    logger.warning(f"Failed to update chat history. Invalid chat_id format '{chat_id}'")
            else:
                # Create a new conversation thread
                title = message[:30] + "..." if len(message) > 30 else message
                new_chat = {
                    "user_id": user_id,
                    "title": title,
                    "messages": [user_msg, bot_msg],
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC)
                }
                res = chats_collection.insert_one(new_chat)
                logger.info(f"Created new chat thread '{res.inserted_id}' for user '{user_id}'")
                
                # Emit newly generated chat_id back to client
                new_id_data = {"new_chat_id": str(res.inserted_id), "title": title}
                yield f"data: {json.dumps(new_id_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            # DB save failure shouldn't crash an already completed stream, just log it
            logger.error(f"Failed to save chat history to database: {e}", exc_info=True)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, user_id: Optional[str] = Depends(get_current_user_optional)):
    logger.info(f"Chat request received. User ID: '{user_id}', Chat ID: '{request.chat_id}'")
    return StreamingResponse(
        chat_generator(request.message, request.history, request.chat_id, user_id),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application via Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)