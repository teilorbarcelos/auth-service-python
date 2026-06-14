import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.modules.health.router import check_database


@pytest.mark.asyncio
class TestHealthRouter:
    async def test_health_success(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert data["checks"]["database"]["status"] == "OK"

    async def test_health_router_success_direct(self):
        res = await check_database()
        assert res["status"] == "OK"

    async def test_health_degraded_db_failure(self, client: AsyncClient):
        with patch("src.modules.health.router.get_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("DB Connection Refused")
            mock_session_ctx.return_value.__aenter__.return_value = mock_session

            response = await client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "DEGRADED"
            assert data["checks"]["database"]["status"] == "ERROR"

    async def test_health_degraded_redis_failure(self, client: AsyncClient):
        with patch("src.infra.redis.redis_provider.redis_provider.client.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.side_effect = Exception("Redis Connection Refused")

            response = await client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "DEGRADED"
            assert data["checks"]["redis"]["status"] == "ERROR"

    async def test_health_uptime_calc(self, client: AsyncClient):
        response = await client.get("/health")
        assert "uptime" in response.json()

    async def test_health_uptime_fallback(self, client: AsyncClient):
        with patch("os.path.exists", side_effect=lambda p: False if p == "/proc/uptime" else True):
            response = await client.get("/health")
            assert response.status_code == 200
            assert "uptime" in response.json()

    async def test_health_uptime_exception(self, client: AsyncClient):
        import builtins

        original_open = builtins.open

        def mocked_open(file, *args, **kwargs):
            if file == "/proc/uptime":
                raise Exception("Read Error")
            return original_open(file, *args, **kwargs)

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=mocked_open):
                response = await client.get("/health")
                assert response.status_code == 200
                assert "uptime" in response.json()

    async def test_liveness(self, client: AsyncClient):
        response = await client.get("/liveness")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_ready(self, client: AsyncClient):
        response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    async def test_ready_degraded(self, client: AsyncClient):
        with patch("src.infra.redis.redis_provider.redis_provider.client.ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.side_effect = Exception("Redis Connection Refused")

            response = await client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not ready"
