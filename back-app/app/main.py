from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.routes import router
from app.app_context import AppContext
from app.core.config import APP_NAME, APP_VERSION
from app.core.errors import AppError
from app.core.responses import fail
from app.core.security import scrub_sensitive


def create_app(context: AppContext | None = None) -> FastAPI:
    ctx = context or AppContext()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ctx = ctx
        try:
            yield
        finally:
            app.state.ctx.close()

    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.state.ctx = ctx

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return fail(exc, request)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        error = AppError(
            "VALIDATION_ERROR",
            "请求参数校验失败",
            status_code=422,
            details={"errors": scrub_sensitive(exc.errors())},
        )
        return fail(error, request)

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        error = AppError(
            "INTERNAL_SERVER_ERROR",
            "后端内部错误",
            status_code=500,
            details={"error": str(exc)},
        )
        return fail(error, request)

    app.include_router(router)

    @app.get("/")
    async def root() -> JSONResponse:
        return JSONResponse({"name": APP_NAME, "version": APP_VERSION, "api": "/api/health"})

    return app


app = create_app()
