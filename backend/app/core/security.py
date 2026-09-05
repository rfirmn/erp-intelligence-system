from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from fastapi import Depends, Header
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default development mock user when SECURITY_ENABLED=false
def get_dev_user() -> Dict[str, Any]:
    return {
        "id": settings.DEV_USER_ID,
        "username": settings.DEV_USER_USERNAME,
        "full_name": settings.DEV_USER_FULL_NAME,
        "role": settings.DEV_USER_ROLE,
        "permissions": [
            "dashboard:read",
            "commercial:read",
            "finance:read",
            "procurement:read",
            "inventory:read",
            "asset:read",
            "service:read",
        ],
    }


DEV_USER: Dict[str, Any] = get_dev_user()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(message="Token autentikasi telah kedaluwarsa.")
    except jwt.PyJWTError:
        raise UnauthorizedError(message="Token autentikasi tidak valid atau tanda tangan rusak.")


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Dependency that returns the current authenticated user.
    Bypasses token verification if SECURITY_ENABLED is False (development mode).
    """
    if not settings.SECURITY_ENABLED:
        return DEV_USER

    if not authorization:
        raise UnauthorizedError(message="Header 'Authorization' tidak disertakan.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError(message="Format Authorization header harus 'Bearer <token>'.")

    token = parts[1]
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise UnauthorizedError(message="Payload token tidak valid (sub claim hilang).")

    return {
        "id": payload.get("user_id", settings.DEV_USER_ID),
        "username": username,
        "full_name": payload.get("full_name", username),
        "role": payload.get("role", "user"),
        "permissions": payload.get("permissions", ["dashboard:read"]),
    }
