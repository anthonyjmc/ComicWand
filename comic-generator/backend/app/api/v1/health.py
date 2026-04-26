"""Health-check endpoints for service readiness and liveness."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    """Return basic health status for orchestration probes."""
    return {"status": "ok"}
