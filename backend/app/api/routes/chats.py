import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.db.mongo import chats_collection

logger = logging.getLogger("server")

router = APIRouter(prefix="/api/chats", tags=["history"])


@router.get("")
def get_user_chats(user_id: str = Depends(get_current_user)):
    try:
        chats = list(chats_collection().find({"user_id": user_id}).sort("updated_at", -1))
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


@router.get("/{chat_id}")
def get_chat_detail(chat_id: str, user_id: str = Depends(get_current_user)):
    try:
        # Catch invalid ObjectId string formats (e.g. invalid 24-hex string)
        obj_id = ObjectId(chat_id)
    except InvalidId:
        logger.warning(f"Invalid ObjectId format provided: '{chat_id}'")
        raise HTTPException(status_code=400, detail="Invalid chat ID format")

    try:
        chat = chats_collection().find_one({"_id": obj_id, "user_id": user_id})
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
