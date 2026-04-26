"""Database models for comic generation jobs and individual pages."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ComicStatus(str, enum.Enum):
    """Lifecycle states for comic generation."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PageStatus(str, enum.Enum):
    """Lifecycle states for generated comic pages."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Comic(Base):
    """Comic generation entity with metadata and final output URLs."""

    __tablename__ = "comics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ComicStatus] = mapped_column(Enum(ComicStatus, name="comic_status"), nullable=False, default=ComicStatus.pending)
    pages_count: Mapped[int] = mapped_column(Integer, nullable=False)
    style: Mapped[str] = mapped_column(String(120), nullable=False)
    reference_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"), server_default="0")

    user = relationship("User", back_populates="comics")
    pages = relationship("ComicPage", back_populates="comic", cascade="all, delete-orphan")


class ComicPage(Base):
    """Per-page generated assets and dialogue payloads."""

    __tablename__ = "comic_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comics.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    panel_count: Mapped[int] = mapped_column(Integer, nullable=False)
    image_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dialogue: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[PageStatus] = mapped_column(Enum(PageStatus, name="page_status"), nullable=False, default=PageStatus.pending)

    comic = relationship("Comic", back_populates="pages")
