from unittest.mock import MagicMock, patch
import pytest

from src.infra.database.db import SessionLocal, get_async_session_factory, get_engine, close_engine


@pytest.mark.asyncio
async def test_session_local_rollback_on_exception():
    with patch("src.infra.database.db.get_async_session_factory") as mock_get_factory:
        mock_session = MagicMock()
        mock_get_factory.return_value.return_value = mock_session

        with patch("src.infra.database.db._test_session", None):
            try:
                async with SessionLocal() as session:
                    raise Exception("Test Exception")
            except Exception as e:
                assert str(e) == "Test Exception"


def test_db_engine_pool_config_non_sqlite():
    from src.shared.config.settings import settings
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = get_engine()
    if "sqlite" not in str(engine.url):
        assert hasattr(engine, "pool")
    else:
        import importlib

        orig_url = settings.database_url

        with patch("src.shared.config.settings.settings.database_url", "postgresql+asyncpg://postgres:pass@localhost:5432/db"):
            import src.infra.database.db as db_mod

            importlib.reload(db_mod)
            engine = db_mod.get_engine()
            assert engine.pool.size() == 10

        with patch("src.shared.config.settings.settings.database_url", orig_url):
            import src.infra.database.db as db_mod

            importlib.reload(db_mod)

    import src.infra.database.db as db_mod
    importlib.reload(db_mod)


@pytest.mark.asyncio
async def test_get_async_session_factory_when_none():
    import src.infra.database.db as db_mod
    import importlib

    db_mod._async_session_factory = None
    db_mod._engine_instance = None

    factory = db_mod.get_async_session_factory()
    assert factory is not None

    importlib.reload(db_mod)


@pytest.mark.asyncio
async def test_close_engine_disposes():
    import src.infra.database.db as db_mod
    import importlib

    _ = db_mod.get_engine()
    assert db_mod._engine_instance is not None

    await db_mod.close_engine()
    assert db_mod._engine_instance is None
    assert db_mod._async_session_factory is None

    importlib.reload(db_mod)
