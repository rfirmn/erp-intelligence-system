from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from fastapi import Depends, Header
import bcrypt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

# Default development mock user when SECURITY_ENABLED=false
def get_dev_user() -> Dict[str, Any]:
    return {
        "id": settings.DEV_USER_ID,
        "username": settings.DEV_USER_USERNAME,
        "full_name": settings.DEV_USER_FULL_NAME,
        "email": settings.DEV_USER_USERNAME,
        "is_active": True,
    }


DEV_USER: Dict[str, Any] = get_dev_user()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


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
        "id": str(payload.get("user_id", settings.DEV_USER_ID)),
        "username": username,
        "full_name": payload.get("full_name", username),
        "email": payload.get("email", username),
        "is_active": payload.get("is_active", True),
    }
