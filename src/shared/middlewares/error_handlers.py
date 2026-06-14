import traceback
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.shared.config.settings import settings


def _is_production() -> bool:
    return settings.environment == "production"


def _problem_detail(status: int, title: str, detail: Any = None, type_: str = None) -> dict:
    if isinstance(detail, str):
        detail_str = detail
    elif detail is not None:
        detail_str = str(detail)
    else:
        detail_str = title
    return {
        "type": type_ or f"https://httpstatuses.io/{status}",
        "title": title,
        "status": status,
        "detail": detail_str,
        "message": title,
    }


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    detail = exc.errors() if not _is_production() else "Validation Error"
    problem = _problem_detail(422, "Validation Error", detail)
    return JSONResponse(status_code=422, content=problem)


async def http_exception_handler(request: Request, exc: HTTPException):
    error_type = getattr(exc, "error_type", "HTTPException")
    detail = exc.detail if not _is_production() else None
    problem = _problem_detail(exc.status_code, exc.detail, detail)
    if exc.status_code == 401:
        problem["error"] = "UnauthorizedError"
    return JSONResponse(status_code=exc.status_code, content=problem)


async def global_exception_handler(request: Request, exc: Exception):
    stack = traceback.format_exc() if not _is_production() else None
    detail = str(exc) if not _is_production() else None
    problem = _problem_detail(500, "Internal Server Error", detail)
    return JSONResponse(status_code=500, content=problem)
