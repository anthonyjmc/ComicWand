"""Centralized application settings and environment validation."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production"] = Field(alias="ENVIRONMENT")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    replicate_api_token: str = Field(alias="REPLICATE_API_TOKEN")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    cloudflare_r2_bucket: str = Field(alias="CLOUDFLARE_R2_BUCKET")
    cloudflare_r2_access_key: str = Field(alias="CLOUDFLARE_R2_ACCESS_KEY")
    cloudflare_r2_secret_key: str = Field(alias="CLOUDFLARE_R2_SECRET_KEY")
    cloudflare_r2_endpoint: str = Field(alias="CLOUDFLARE_R2_ENDPOINT")
    clerk_secret_key: str = Field(alias="CLERK_SECRET_KEY")
    clerk_webhook_secret: str = Field(alias="CLERK_WEBHOOK_SECRET")
    allowed_origins: str = Field(alias="ALLOWED_ORIGINS")
    max_pages_per_comic: int = Field(default=48, alias="MAX_PAGES_PER_COMIC")
    max_comics_per_day: int = Field(default=5, alias="MAX_COMICS_PER_DAY")
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")

    request_limit_per_minute_free: int = 20
    request_limit_per_hour_free: int = 100
    comic_limit_per_day_free: int = 5
    request_limit_per_minute_pro: int = 60
    request_limit_per_hour_pro: int = 300
    comic_limit_per_day_pro: int = 25

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure database URL is a PostgreSQL DSN."""
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use a postgresql driver")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        """Ensure Redis URL format is valid."""
        if not value.startswith("redis://") and not value.startswith("rediss://"):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
        return value

    @property
    def is_production(self) -> bool:
        """Return whether current environment is production."""
        return self.environment == "production"

    @property
    def parsed_allowed_origins(self) -> list[str]:
        """Split ALLOWED_ORIGINS into normalized list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def get_tier_limits(self, tier: str) -> dict[str, int]:
        """Get configured limits for a user tier."""
        if tier == "pro":
            return {
                "per_minute": self.request_limit_per_minute_pro,
                "per_hour": self.request_limit_per_hour_pro,
                "per_day_comics": self.comic_limit_per_day_pro,
            }
        return {
            "per_minute": self.request_limit_per_minute_free,
            "per_hour": self.request_limit_per_hour_free,
            "per_day_comics": self.comic_limit_per_day_free,
        }


class DevelopmentSettings(Settings):
    """Development-specific settings."""

    environment: Literal["development"] = Field(default="development", alias="ENVIRONMENT")


class ProductionSettings(Settings):
    """Production-specific settings."""

    environment: Literal["production"] = Field(default="production", alias="ENVIRONMENT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached validated settings, failing fast at startup."""
    try:
        base_settings = Settings()
        if base_settings.environment == "production":
            return ProductionSettings()
        return DevelopmentSettings()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid environment configuration: {exc}") from exc

