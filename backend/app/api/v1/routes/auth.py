from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import col, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.datetime_utils import utc_now
from app.core.security import create_access_token, get_current_user, verify_password
from app.core.session import get_db
from app.models.users import DimUser
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.envelope import ResponseEnvelope, success_response

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login Pengguna Dashboard",
    description="Memvalidasi kredensial pengguna terhadap basis data dan menghasilkan access token JWT Bearer.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)

    # 1. Query user from feature_store.dim_user by username or email
    stmt = select(DimUser).where(
        or_(col(DimUser.username) == payload.username, col(DimUser.email) == payload.username)
    )
    res = await session.execute(stmt)
    user = res.scalars().first()

    # 2. Check user existence, active status, and password verification
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kredensial tidak valid: username atau password salah.",
        )

    # 3. Update last login timestamp
    user.last_login_at = utc_now()
    await session.commit()
    await session.refresh(user)

    user_info = UserResponse(
        id=str(user.id),
        username=user.username,
        full_name=user.full_name or user.username,
        email=user.email,
        is_active=user.is_active,
    )

    token = create_access_token(
        data={
            "sub": user.username,
            "user_id": str(user.id),
            "full_name": user_info.full_name,
            "email": user.email,
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
    description="Mengembalikan profil pengguna terotentikasi dari token JWT aktif.",
)
async def get_profile(request: Request, current_user: dict = Depends(get_current_user)):
    request_id = getattr(request.state, "request_id", None)
    user_data = UserResponse(
        id=str(current_user.get("id", settings.DEV_USER_ID)),
        username=current_user.get("username", settings.DEV_USER_USERNAME),
        full_name=current_user.get("full_name", settings.DEV_USER_FULL_NAME),
        email=current_user.get("email", settings.DEV_USER_USERNAME),
        is_active=current_user.get("is_active", True),
    )
    return success_response(data=user_data.model_dump(), request_id=request_id)
