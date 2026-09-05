import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.session import ensure_default_dashboard_user
from app.main import app
from app.schemas.auth import TokenResponse, UserResponse


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_auth_db_login_success_and_profile(client: AsyncClient):
    # Ensure default user is seeded
    await ensure_default_dashboard_user()

    # 1. Login with correct credentials
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.DEV_USER_USERNAME,
            "password": settings.DEV_USER_PASSWORD,
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["success"] is True
    assert "access_token" in login_data["data"]
    assert login_data["data"]["token_type"] == "bearer"

    user_info = login_data["data"]["user"]
    assert user_info["username"] == settings.DEV_USER_USERNAME
    assert user_info["is_active"] is True
    # Ensure role and permissions are absent
    assert "role" not in user_info
    assert "permissions" not in user_info

    token = login_data["data"]["access_token"]

    # 2. Query /auth/me with Bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["success"] is True
    assert me_data["data"]["username"] == settings.DEV_USER_USERNAME
    assert me_data["data"]["is_active"] is True
    assert "role" not in me_data["data"]
    assert "permissions" not in me_data["data"]


@pytest.mark.asyncio
async def test_auth_db_login_invalid_password(client: AsyncClient):
    await ensure_default_dashboard_user()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.DEV_USER_USERNAME,
            "password": "WrongPassword999!",
        },
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_db_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent_user_99@isp.net",
            "password": "SomePassword123!",
        },
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_me_unauthorized_when_security_enabled(client: AsyncClient, monkeypatch):
    # Enforce security verification
    monkeypatch.setattr(settings, "SECURITY_ENABLED", True)

    # Missing authorization header
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"

    # Invalid token format
    bad_token_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert bad_token_resp.status_code == 401
    bad_payload = bad_token_resp.json()
    assert bad_payload["success"] is False
    assert bad_payload["error"]["code"] == "UNAUTHORIZED"
