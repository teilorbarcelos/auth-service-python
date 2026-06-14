import datetime
import logging
import os

from fastapi import APIRouter, Response
from sqlalchemy import text

from src.infra.database.db import get_session
from src.infra.redis.redis_provider import redis_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

START_TIME = datetime.datetime.now()


def get_uptime():
    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime") as f:
                uptime_seconds = int(float(f.readline().split()[0]))
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60
                seconds = uptime_seconds % 60
                return f"{days}d {hours}h {minutes}m {seconds}s"
        except Exception:
            pass

    delta = datetime.datetime.now() - START_TIME
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


async def check_database():
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "OK", "message": "Connected"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


async def check_redis():
    try:
        await redis_provider.client.ping()
        return {"status": "OK", "message": "Connected"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@router.get("/health")
async def health_check(response: Response):
    status = "UP"
    db_check = await check_database()
    redis_check = await check_redis()

    checks = {"database": db_check, "redis": redis_check}

    for name, check in checks.items():
        if check["status"] != "OK":
            status = "DEGRADED"
            logger.warning(f"System Health Degraded: {name} is down", extra={"check": name, "details": check["message"]})

    data = {
        "status": status,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deploy": {"timestamp": None, "version": None},
        "uptime": get_uptime(),
        "checks": checks,
        "message": "API is running smoothly. All systems operational.",
    }

    response.status_code = 200 if status == "UP" else 503
    return data


@router.get("/liveness")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response):
    db_check = await check_database()
    redis_check = await check_redis()

    if db_check["status"] == "OK" and redis_check["status"] == "OK":
        return {"status": "ready"}

    response.status_code = 503
    return {"status": "not ready", "database": db_check, "redis": redis_check}
