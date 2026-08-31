import os
import jwt
import bcrypt  # Import trực tiếp bcrypt thay vì passlib
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from core.setup_logging import setup_logging
from core.load_settings import load_settings
import logging 

settings = load_settings()
setup_logging()
logger = logging.getLogger("backend")

load_dotenv()

SECRET_KEY = settings['backend']['jwt_secret']
ALGORITHM = settings['backend']['jwt_algorithm']

security = HTTPBearer(auto_error=False)

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
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")  
    except Exception:
        logger.warning("Invalid JWT token")
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = get_current_user_optional(credentials)
    if not user:
        logger.error("Unauthorized access attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user