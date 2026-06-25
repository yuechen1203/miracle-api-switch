from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.errors import AppError
from app.core.security import scrub_sensitive


def get_request_id(request: Request | None = None) -> str | None:
    if request is None:
        return None
    return getattr(request.state, "request_id", None)


def ok(data: Any, request: Request | None = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "success": True,
                "data": data,
                "error": None,
                "request_id": get_request_id(request),
            }
        ),
    )


def fail(error: AppError, request: Request | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=jsonable_encoder(
            {
                "success": False,
                "data": None,
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": scrub_sensitive(error.details),
                },
                "request_id": get_request_id(request),
            }
        ),
    )

