"""Auth-related endpoints wired to Clerk-backed identity."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def read_current_user(user: dict = Depends(get_current_user)) -> dict:
    """Return authenticated user claims."""
    return {"user": user}
