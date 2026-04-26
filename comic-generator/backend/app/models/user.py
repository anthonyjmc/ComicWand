"""Database model for authenticated Comic Generator users."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserTier(str, enum.Enum):
    """Supported paid tiers for feature and rate-limit controls."""

    free = "free"
    pro = "pro"


class User(Base):
    """User persisted from Clerk identity and app-specific counters."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    comics_generated_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_comic_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tier: Mapped[UserTier] = mapped_column(Enum(UserTier, name="user_tier"), nullable=False, default=UserTier.free)

    comics = relationship("Comic", back_populates="user", cascade="all, delete-orphan")
