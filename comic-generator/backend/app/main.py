"""FastAPI application entrypoint for Comic Generator backend."""

from __future__ import annotations

import time
import asyncio

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger
from redis.asyncio import Redis
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.extension import _rate_limit_exceeded_handler
from sqlalchemy import text

from app.api.v1 import auth, comics, health
from app.core.config import get_settings
from app.core.database import SessionFactory
from app.core.logging import configure_logging
from app.core.logging import log_api_call
from app.core.rate_limiter import slowapi_limiter
from app.core.security_headers import add_security_headers
from app.workers.celery_app import celery_app

settings = get_settings()
configure_logging()

app = FastAPI(title="Comic Generator API", version="1.0.0")
app.state.limiter = slowapi_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.parsed_allowed_hosts)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    max_bytes = 15 * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": "payload_too_large", "message": "Request body exceeds 15MB limit"},
        )
    return await call_next(request)


app.middleware("http")(add_security_headers)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    user_id = str(getattr(request.state, "user_id", "anonymous"))
    endpoint = f"{request.method} {request.url.path}"
    log_api_call(user_id=user_id, endpoint=endpoint, status_code=response.status_code, duration_ms=duration_ms)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail_text = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": detail_text},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    invalid_fields = []
    for error in exc.errors():
        invalid_fields.append({"field": ".".join(str(item) for item in error.get("loc", [])), "message": error.get("msg")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "message": "Invalid request payload", "fields": invalid_fields},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.bind(user_id="system", action="unhandled_exception", duration_ms=0).exception(
        "Unhandled exception type={error_type}",
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_server_error", "message": "Internal server error"},
    )


@app.get("/health")
async def health_check() -> dict[str, object]:
    db_ok = False
    redis_ok = False
    workers = 0

    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        redis_ok = bool(await redis_client.ping())
    except Exception:
        redis_ok = False
    finally:
        await redis_client.aclose()

    try:
        inspect_result = await asyncio.to_thread(celery_app.control.inspect().active)
        active_workers = inspect_result or {}
        workers = len(active_workers.keys())
    except Exception:
        workers = 0

    health_status = "healthy" if db_ok and redis_ok else "unhealthy"
    return {"status": health_status}

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(comics.router, prefix="/api/v1")
