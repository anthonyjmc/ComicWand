"""Application logging configuration using loguru."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure environment-aware log formatting and levels."""
    settings = get_settings()
    logger.remove()

    log_level = "INFO" if settings.is_production else "DEBUG"
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | "
            "user_id={extra[user_id]} action={extra[action]} duration_ms={extra[duration_ms]} | {message}"
        ),
        enqueue=True,
        backtrace=not settings.is_production,
        diagnose=not settings.is_production,
    )


def _safe_endpoint(endpoint: str) -> str:
    """Prevent accidental logging of secret-like endpoint strings."""
    lower_endpoint = endpoint.lower()
    sensitive_keywords = ("token", "key", "secret", "password")
    if any(keyword in lower_endpoint for keyword in sensitive_keywords):
        return "redacted-endpoint"
    return endpoint


def log_api_call(user_id: str, endpoint: str, status_code: int, duration_ms: int) -> None:
    """Emit normalized API call logs without leaking sensitive data."""
    safe_user_id = user_id if user_id else "anonymous"
    safe_action = _safe_endpoint(endpoint)
    logger.bind(user_id=safe_user_id, action=safe_action, duration_ms=duration_ms).info(
        "api_call status_code={status_code}",
        status_code=status_code,
    )
