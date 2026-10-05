import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

logger = logging.getLogger("server")

security = HTTPBearer(auto_error=False)


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    return decode_access_token(credentials.credentials)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = get_current_user_optional(credentials)
    if not user:
        logger.error("Unauthorized access attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
