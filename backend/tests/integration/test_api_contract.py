import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.envelope import ResponseEnvelope
from app.schemas.health import HealthResponse
from app.schemas.insights import InsightPackage


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint_contract(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    # Validate universal envelope
    assert payload["success"] is True
    assert payload["error"] is None
    assert "request_id" in payload["meta"]
    assert "timestamp" in payload["meta"]

    # Validate data matches HealthResponse schema
    health = HealthResponse(**payload["data"])
    assert health.status in ("healthy", "degraded")
    assert "staging" in health.components.feature_store.schemas


@pytest.mark.asyncio
async def test_auth_login_contract(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin@isp.net", "password": "SecretPassword123!"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "access_token" in payload["data"]
    assert payload["data"]["token_type"] == "bearer"
    assert payload["data"]["user"]["username"] == "admin@isp.net"


@pytest.mark.asyncio
async def test_auth_me_contract(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["role"] == "admin"
    assert "dashboard:read" in payload["data"]["permissions"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module",
    [
        "overview",
        "commercial",
        "finance",
        "procurement",
        "inventory",
        "asset",
        "service",
    ],
)
async def test_mock_insights_all_modules_contract(client: AsyncClient, module: str):
    response = await client.get(f"/api/v1/insights/mock/{module}")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert "request_id" in payload["meta"]

    # Validate full InsightPackage structure via Pydantic
    package = InsightPackage(**payload["data"])
    assert package.module == module
    assert len(package.key_metrics) > 0
    assert len(package.visualizations) > 0
    assert package.visualizations[0].chart_library == "vega-lite"
    assert "mark" in package.visualizations[0].spec


@pytest.mark.asyncio
async def test_validation_error_envelope(client: AsyncClient):
    # Missing username and invalid password
    response = await client.post(
        "/api/v1/auth/login",
        json={"password": "1"},  # username missing, password < 4 chars
    )
    assert response.status_code == 400

    payload = response.json()
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert len(payload["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_not_found_error_envelope(client: AsyncClient):
    response = await client.get("/api/v1/insights/mock/unrecognized_module")
    assert response.status_code == 404

    payload = response.json()
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "NOT_FOUND"
