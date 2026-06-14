import os
import subprocess
import sys

from src.infra.database.db import get_session
from src.shared.utils.logging import get_logger
from src.shared.utils.seed_helpers import seed_admin, seed_features, seed_roles

logger = get_logger("bootstrap")


AUTH_HEAD_REV = "923509e24aee"
BACKEND_HEAD_REV = "a1b2c3d4e5f6"


async def _stamp_if_needed() -> bool:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=root_dir, capture_output=True, text=True, check=False
        )
        current = result.stdout.strip()
        if current and current != AUTH_HEAD_REV and BACKEND_HEAD_REV in current:
            logger.info("DB at backend revision — skipping stamp, schema already compatible.")
            return False
        if current and current != AUTH_HEAD_REV:
            logger.info("Stamping DB to auth head revision...")
            subprocess.run(
                [sys.executable, "-m", "alembic", "stamp", AUTH_HEAD_REV],
                cwd=root_dir, check=True
            )
        return True
    except Exception as e:
        logger.warning(f"Migration stamp check failed: {e}")
        return False


async def run_migrations():
    logger.info("Running database migrations...")
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if not await _stamp_if_needed():
            return
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "heads"], cwd=root_dir, check=True)
        logger.info("Migrations applied successfully.")
    except Exception as e:
        logger.error(f"Failed to apply migrations: {e}")


async def bootstrap_system():

    await run_migrations()

    async with get_session() as session:
        await seed_features(session)
        await seed_roles(session)
        await seed_admin(session)
        await session.commit()
