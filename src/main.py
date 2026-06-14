import os
import sys

IS_TEST = "pytest" in sys.modules or "test" in "".join(sys.argv)


from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from src.infra.database.db import close_engine, get_engine
from src.shared.middlewares.error_handlers import global_exception_handler, http_exception_handler, validation_exception_handler
from src.shared.utils.logging import get_logger

logger = get_logger("main")
from contextlib import asynccontextmanager

from src.modules.auth.router import router as auth_router
from src.modules.health.router import router as health_router
from src.shared.config.settings import settings
from src.shared.middlewares.logging_middleware import logging_middleware
from src.shared.middlewares.rate_limit_middleware import rate_limit_middleware
from src.shared.utils.bootstrap import bootstrap_system


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not IS_TEST:
        get_engine()
        await bootstrap_system()

    yield

    if not IS_TEST:
        try:
            await close_engine()
        except Exception:
            pass
        from src.infra.redis.redis_provider import redis_provider

        try:
            await redis_provider.client.aclose()
        except Exception:
            pass


app = FastAPI(title="Auth Service Python", lifespan=lifespan, docs_url="/v1/docs", openapi_url="/v1/swagger.json")

allowed_origins = settings.cors_allowed_origins.split(",") if settings.cors_allowed_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if settings.cors_allowed_origins != "*" else False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
)

if settings.environment == "production":
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in settings.cors_allowed_origins.split(",") if h.strip()],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)


@app.middleware("http")
async def logging(request: Request, call_next):
    return await logging_middleware(request, call_next)


app.include_router(auth_router)
app.include_router(health_router)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

import logging


class HealthLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthLogFilter())
