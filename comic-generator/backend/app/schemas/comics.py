"""Schemas for comic API payloads and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ComicStyle(str, Enum):
    """Allowed comic art styles."""

    manga = "manga"
    western = "western"
    superhero = "superhero"
    cartoon = "cartoon"
    noir = "noir"


class CreateComicRequest(BaseModel):
    """Validated create-comic payload for docs and internal mapping."""

    story_prompt: str = Field(min_length=10, max_length=2000, description="Story prompt for comic generation")
    pages: int = Field(ge=1, le=48, description="Number of pages to generate")
    style: ComicStyle = Field(description="Visual style for comic pages")
    title: str = Field(min_length=5, max_length=100, description="Comic title")

    @field_validator("story_prompt", "title")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("String field cannot be empty")
        return cleaned_value

    model_config = {"from_attributes": True}


class ComicResponse(BaseModel):
    """Public comic response shape without sensitive fields."""

    comic_id: UUID = Field(description="Comic UUID")
    status: str = Field(description="Current comic status")
    estimated_minutes: float = Field(description="Estimated generation time")

    model_config = {"from_attributes": True}


class ComicStatusResponse(BaseModel):
    """Status response for a specific comic."""

    comic_id: UUID = Field(description="Comic UUID")
    status: str = Field(description="Current comic status")
    progress: int | None = Field(default=None, description="Generation progress percentage")
    pdf_url: str | None = Field(default=None, description="Signed PDF URL when completed")
    error_message: str | None = Field(default=None, description="Generic user-safe error message")

    model_config = {"from_attributes": True}


class ComicListItem(BaseModel):
    """List item for user comic collection."""

    id: UUID = Field(description="Comic UUID")
    title: str = Field(description="Comic title")
    status: str = Field(description="Comic status")
    pages_count: int = Field(description="Requested page count")
    style: str = Field(description="Comic visual style")
    created_at: datetime = Field(description="Creation timestamp")
    pdf_url: str | None = Field(default=None, description="Signed PDF URL for completed comics")

    model_config = {"from_attributes": True}


class ComicListResponse(BaseModel):
    """Paginated comic list response."""

    items: list[ComicListItem] = Field(description="Paginated list of comics")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Offset used in query")
    total: int = Field(description="Total comics for user")

    model_config = {"from_attributes": True}


class ComicPageResponse(BaseModel):
    """Generated page output representation."""

    page_number: int = Field(description="Page number in comic sequence")
    image_url: str = Field(description="Public or signed URL for page image")

    model_config = {"from_attributes": True}
