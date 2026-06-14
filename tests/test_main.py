from unittest.mock import patch, AsyncMock
import logging

import pytest
from httpx import AsyncClient

from src.main import app, HealthLogFilter


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
    assert response.headers.get("Strict-Transport-Security") is not None


def test_health_log_filter_blocks_health():
    filt = HealthLogFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "/health check", (), None)
    assert filt.filter(record) is False


def test_health_log_filter_passes_non_health():
    filt = HealthLogFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "/api/login", (), None)
    assert filt.filter(record) is True


async def test_lifespan_startup_shutdown():
    import src.main as main_module
    from src.main import lifespan, app

    with patch.object(main_module, "IS_TEST", False):
        with patch("src.main.get_engine") as mock_get_engine:
            with patch("src.main.bootstrap_system", new_callable=AsyncMock) as mock_bootstrap:
                with patch("src.main.close_engine", new_callable=AsyncMock) as mock_close:
                    from src.infra.redis.redis_provider import redis_provider

                    with patch.object(redis_provider.client, "aclose", new_callable=AsyncMock) as mock_redis_close:
                        async with lifespan(app):
                            pass

                        mock_get_engine.assert_called_once()
                        mock_bootstrap.assert_called_once()
                        mock_close.assert_called_once()
                        mock_redis_close.assert_called_once()


async def test_lifespan_shutdown_exceptions():
    import src.main as main_module
    from src.main import lifespan, app

    with patch.object(main_module, "IS_TEST", False):
        with patch("src.main.get_engine"):
            with patch("src.main.bootstrap_system", new_callable=AsyncMock):
                with patch("src.main.close_engine", new_callable=AsyncMock, side_effect=Exception("Close failed")):
                    from src.infra.redis.redis_provider import redis_provider

                    with patch.object(redis_provider.client, "aclose", new_callable=AsyncMock, side_effect=Exception("Redis close failed")):
                        async with lifespan(app):
                            pass


async def test_trusted_host_middleware_production():
    import importlib
    from src.shared.config.settings import settings

    orig_env = settings.environment
    orig_origins = settings.cors_allowed_origins

    try:
        settings.environment = "production"
        settings.cors_allowed_origins = "test.com"

        import src.main as main_mod

        importlib.reload(main_mod)

        middleware_names = [m.cls.__name__ for m in main_mod.app.user_middleware]
        assert "TrustedHostMiddleware" in middleware_names
    finally:
        settings.environment = orig_env
        settings.cors_allowed_origins = orig_origins
        import src.main as main_mod

        importlib.reload(main_mod)
