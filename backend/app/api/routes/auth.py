import logging
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongo import users_collection

logger = logging.getLogger("server")

router = APIRouter(prefix="/api", tags=["auth"])


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: AuthRequest):
    logger.info(f"Registration attempt for username: '{req.username}'")
    try:
        users = users_collection()
        if users.find_one({"username": req.username}):
            logger.warning(f"Registration failed: Username '{req.username}' already exists.")
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed = hash_password(req.password)
        user_doc = {
            "username": req.username,
            "password": hashed,
            "created_at": datetime.now(UTC)
        }
        result = users.insert_one(user_doc)
        token = create_access_token({"sub": str(result.inserted_id), "username": req.username})

        logger.info(f"User '{req.username}' registered successfully with ID: {result.inserted_id}")
        return {"token": token, "username": req.username}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration for '{req.username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during registration")


@router.post("/login")
def login(req: AuthRequest):
    logger.info(f"Login attempt for username: '{req.username}'")
    try:
        user = users_collection().find_one({"username": req.username})
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
