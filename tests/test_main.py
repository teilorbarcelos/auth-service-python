from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_should_build_the_app_correctly():
    assert app is not None
    assert app.title == "Auth Service Python"


@pytest.mark.asyncio
async def test_should_have_health_and_liveness_endpoints(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"

    response = await client.get("/liveness")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_should_return_422_on_validation_error(client: AsyncClient):
    response = await client.post("/v1/auth/login", json={"invalid": "payload"})
    assert response.status_code == 422
    assert response.json()["message"] == "Validation Error"


@pytest.mark.asyncio
async def test_global_exception_handler_direct(client: AsyncClient):
    from unittest.mock import MagicMock

    from src.shared.middlewares.error_handlers import global_exception_handler

    request = MagicMock()
    request.method = "GET"
    request.url = "http://test"
    request.state.user = {"id": "user-123", "email": "test@test.com"}

    exc = Exception("Test Crash")

    response = await global_exception_handler(request, exc)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_audit_middleware_with_unreadable_body(client: AsyncClient):
    response = await client.post("/v1/auth/login", content=b"\xff", headers={"Content-Type": "application/json"})
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_security_headers_on_response(client: AsyncClient):
    response = await client.get("/liveness")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Strict-Transport-Security") is not None
