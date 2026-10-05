import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.core.config import load_settings

logger = logging.getLogger("server")


def _jwt_settings() -> tuple[str, str]:
    backend = load_settings()['backend']
    return backend['jwt_secret'], backend['jwt_algorithm']


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)) -> str:
    secret, algorithm = _jwt_settings()
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_access_token(token: str) -> Optional[str]:
    """Return the user id (`sub`) of a valid token, otherwise None."""
    secret, algorithm = _jwt_settings()
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        logger.warning("Invalid JWT token")
        return None
