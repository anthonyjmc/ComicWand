"""Comic generation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.rate_limiter import check_rate_limit
from app.core.security import sanitize_prompt

router = APIRouter(prefix="/comics", tags=["comics"])


class CreateComicRequest(BaseModel):
    """Request payload to start a comic generation workflow."""

    title: str = Field(min_length=1, max_length=255)
    story_prompt: str = Field(min_length=1, max_length=2000)
    pages_count: int = Field(ge=1, le=48)


@router.post("", dependencies=[Depends(check_rate_limit)])
async def create_comic(payload: CreateComicRequest) -> dict[str, str]:
    """Validate payload and enqueue comic generation."""
    clean_prompt = sanitize_prompt(payload.story_prompt)
    if not clean_prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt is invalid")
    return {"status": "queued", "title": payload.title}
