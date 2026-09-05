from fastapi import APIRouter, Depends, Request, status

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.envelope import ResponseEnvelope, success_response

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login Pengguna",
    description="Menghasilkan access token JWT Bearer untuk mengakses endpoint terlindungi.",
)
async def login(payload: LoginRequest, request: Request):
    request_id = getattr(request.state, "request_id", None)

    # In development or initial setup, grant token with admin role
    # User credential management can be hooked to DB in later phase
    user_info = UserResponse(
        id="usr-001",
        username=payload.username,
        full_name="System Administrator" if "admin" in payload.username.lower() else "ISP Operations Analyst",
        role="admin" if "admin" in payload.username.lower() else "analyst",
        permissions=[
            "dashboard:read",
            "commercial:read",
            "finance:read",
            "procurement:read",
            "inventory:read",
            "asset:read",
            "service:read",
        ],
    )

    token = create_access_token(
        data={
            "sub": user_info.username,
            "user_id": user_info.id,
            "full_name": user_info.full_name,
            "role": user_info.role,
            "permissions": user_info.permissions,
        }
    )

    token_data = TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_info,
    )

    return success_response(data=token_data.model_dump(), request_id=request_id)


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Profil Pengguna Aktif",
    description="Mengembalikan profil dan permission pengguna dari token JWT aktif.",
)
async def get_profile(request: Request, current_user: dict = Depends(get_current_user)):
    request_id = getattr(request.state, "request_id", None)
    user_data = UserResponse(
        id=current_user.get("id", "usr-001"),
        username=current_user.get("username", "admin@isp.net"),
        full_name=current_user.get("full_name", "System Administrator"),
        role=current_user.get("role", "admin"),
        permissions=current_user.get("permissions", []),
    )
    return success_response(data=user_data.model_dump(), request_id=request_id)
