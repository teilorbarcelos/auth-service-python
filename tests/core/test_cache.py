import pytest
from unittest.mock import patch, AsyncMock
from src.core.cache import cached, invalidate_cache, REDIS_AVAILABLE
from src.infra.redis.redis_provider import redis_provider


@pytest.mark.asyncio
class TestCacheDecorator:
    async def test_should_bypass_cache_when_redis_unavailable(self):
        with patch("src.core.cache.REDIS_AVAILABLE", False):
            call_count = 0

            @cached(ttl=10)
            async def my_func(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 2

            result1 = await my_func(5)
            result2 = await my_func(5)
            assert result1 == 10
            assert result2 == 10
            assert call_count == 2  # sem cache, chamou 2 vezes

    async def test_should_cache_result_and_return_from_cache(self):
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def my_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value=None) as mock_get:
            with patch.object(redis_provider, "setex", new_callable=AsyncMock) as mock_setex:
                result1 = await my_func(5)
                assert result1 == 10
                assert call_count == 1
                mock_get.assert_called()
                mock_setex.assert_called_once()

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value="10") as mock_get:
            result2 = await my_func(5)
            assert result2 == 10
            assert call_count == 1  # nao incrementou - veio do cache

    async def test_should_handle_json_deserialize_error(self):
        @cached(ttl=60)
        async def my_func() -> str:
            return "fresh"

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value="invalid-json"):
            with patch.object(redis_provider, "setex", new_callable=AsyncMock):
                result = await my_func()
                assert result == "fresh"

    async def test_invalidate_cache_when_redis_unavailable(self):
        with patch("src.core.cache.REDIS_AVAILABLE", False):
            await invalidate_cache("role:")

    async def test_invalidate_cache_handles_error(self):
        if REDIS_AVAILABLE:
            with patch.object(redis_provider.client, "keys", new_callable=AsyncMock, side_effect=Exception("Redis error")):
                await invalidate_cache("role:")

    async def test_invalidate_cache_by_pattern(self):
        from src.core.cache import REDIS_AVAILABLE

        if REDIS_AVAILABLE:
            with patch.object(redis_provider.client, "keys", new_callable=AsyncMock, return_value=["cache:role:admin", "cache:role:user"]):
                with patch.object(redis_provider.client, "delete", new_callable=AsyncMock) as mock_del:
                    await invalidate_cache("role:")
                    mock_del.assert_called_once_with("cache:role:admin", "cache:role:user")

    async def test_should_return_string_cache_non_serialized(self):
        call_count = 0

        @cached(ttl=10, serialize=False)
        async def my_func() -> str:
            nonlocal call_count
            call_count += 1
            return "raw-value"

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value="cached-value"):
            result = await my_func()
            assert result == "cached-value"
            assert call_count == 0

    async def test_should_handle_setex_failure_gracefully(self):
        call_count = 0

        @cached(ttl=10)
        async def my_func() -> str:
            nonlocal call_count
            call_count += 1
            return "result"

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value=None):
            with patch.object(redis_provider, "setex", new_callable=AsyncMock, side_effect=Exception("Redis fail")):
                result = await my_func()
                assert result == "result"
                assert call_count == 1

    async def test_redis_import_failure_coverage(self):
        import importlib
        import sys
        import types

        old_cache_mod = sys.modules.get("src.core.cache")
        old_redis_mod = sys.modules.get("src.infra.redis.redis_provider")

        empty_mod = types.ModuleType("src.infra.redis.redis_provider")

        try:
            sys.modules["src.infra.redis.redis_provider"] = empty_mod
            cm = importlib.import_module("src.core.cache")
            importlib.reload(cm)
            assert cm.REDIS_AVAILABLE is False
        finally:
            if old_redis_mod:
                sys.modules["src.infra.redis.redis_provider"] = old_redis_mod
            if old_cache_mod:
                sys.modules["src.core.cache"] = old_cache_mod
                importlib.reload(sys.modules["src.core.cache"])

    async def test_stampede_lock_with_cache_hit(self):
        from src.core.cache import _STAMPEDE_LOCKS, _wait_for_stampede
        import asyncio

        lock = asyncio.Lock()
        await lock.acquire()
        _STAMPEDE_LOCKS["lock:stampede_cov"] = lock

        try:
            with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value='"cached-val"'):
                result = await _wait_for_stampede("cache:stampede_cov", "lock:stampede_cov", 60, True)
                assert result == "cached-val"
        finally:
            _STAMPEDE_LOCKS.pop("lock:stampede_cov", None)

    async def test_compute_and_cache_double_check_hit(self):
        from src.core.cache import _STAMPEDE_LOCKS, _compute_and_cache
        import asyncio

        _STAMPEDE_LOCKS["lock:dbl_check"] = asyncio.Lock()

        async def fake_func():
            return "fresh"

        try:
            with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value='"cached"'):
                result = await _compute_and_cache(fake_func, (), {}, "cache:dbl_check", 60, True)
                assert result == "cached"
        finally:
            _STAMPEDE_LOCKS.pop("lock:dbl_check", None)

    async def test_stampede_wait_timeout_exception(self):
        from src.core.cache import _STAMPEDE_LOCKS, _wait_for_stampede
        import asyncio

        lock = asyncio.Lock()
        await lock.acquire()
        _STAMPEDE_LOCKS["lock:timeout_test"] = lock

        try:
            with patch.object(redis_provider, "get", new_callable=AsyncMock, side_effect=Exception("Redis timeout")):
                result = await _wait_for_stampede("cache:timeout_test", "lock:timeout_test", 60, True)
                assert result is None
        finally:
            _STAMPEDE_LOCKS.pop("lock:timeout_test", None)

    async def test_decorator_stampede_result_path(self):
        call_count = 0

        @cached(ttl=60)
        async def my_func():
            nonlocal call_count
            call_count += 1
            return "computed"

        with patch.object(redis_provider, "get", new_callable=AsyncMock, return_value=None):
            with patch("src.core.cache._wait_for_stampede", new_callable=AsyncMock, return_value="stampede-value"):
                result = await my_func()
                assert result == "stampede-value"
                assert call_count == 0

    async def test_invalidate_cache_empty_keys(self):
        if REDIS_AVAILABLE:
            with patch.object(redis_provider.client, "keys", new_callable=AsyncMock, return_value=[]):
                await invalidate_cache("nonexistent")

    async def test_stampede_prevention(self):
        import asyncio

        call_count = 0

        @cached(ttl=30, key_prefix="stampede")
        async def slow_func() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return "computed"

        async def always_none(*args, **kwargs):
            return None

        with patch.object(redis_provider, "get", new_callable=AsyncMock, side_effect=always_none):
            with patch.object(redis_provider, "setex", new_callable=AsyncMock):
                results = await asyncio.gather(slow_func(), slow_func(), slow_func())
                assert all(r == "computed" for r in results)
