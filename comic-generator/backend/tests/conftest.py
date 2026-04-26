from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/comic_generator")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REPLICATE_API_TOKEN", "test-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-token")
os.environ.setdefault("CLOUDFLARE_R2_BUCKET", "test-bucket")
os.environ.setdefault("CLOUDFLARE_R2_ACCESS_KEY", "test-key")
os.environ.setdefault("CLOUDFLARE_R2_SECRET_KEY", "test-secret")
os.environ.setdefault("CLOUDFLARE_R2_ENDPOINT", "https://example.r2.cloudflarestorage.com")
os.environ.setdefault("CLERK_SECRET_KEY", "test-clerk-secret")
os.environ.setdefault("CLERK_WEBHOOK_SECRET", "whsec_dGVzdA==")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from app.main import app
from app.models.comic import Comic, ComicStatus
from app.models.user import User, UserTier


class FakeRedisPipeline:
    def __init__(self, redis_store: dict[str, list[int]]) -> None:
        self.redis_store = redis_store
        self.commands: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    def zremrangebyscore(self, key: str, minimum: int, maximum: int) -> None:
        self.commands.append(("zremrangebyscore", key, minimum, maximum))

    def zadd(self, key: str, mapping: dict[str, int]) -> None:
        self.commands.append(("zadd", key, mapping))

    def zcard(self, key: str) -> None:
        self.commands.append(("zcard", key))

    def pexpire(self, key: str, ttl_ms: int) -> None:
        self.commands.append(("pexpire", key, ttl_ms))

    async def execute(self):
        results = []
        for command in self.commands:
            name = command[0]
            if name == "zremrangebyscore":
                _, key, minimum, maximum = command
                items = self.redis_store.get(key, [])
                remaining_items = [item for item in items if not minimum <= item <= maximum]
                deleted = len(items) - len(remaining_items)
                self.redis_store[key] = remaining_items
                results.append(deleted)
                continue
            if name == "zadd":
                _, key, mapping = command
                score = list(mapping.values())[0]
                self.redis_store.setdefault(key, []).append(score)
                results.append(1)
                continue
            if name == "zcard":
                _, key = command
                results.append(len(self.redis_store.get(key, [])))
                continue
            if name == "pexpire":
                results.append(True)
                continue
        self.commands = []
        return results


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, list[int]] = {}

    def pipeline(self, transaction: bool = True) -> FakeRedisPipeline:
        del transaction
        return FakeRedisPipeline(self.store)


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def redis_mock():
    return FakeRedis()


@pytest.fixture
def async_db_session():
    class DummyAsyncSession:
        async def execute(self, statement):
            del statement
            return None

        async def commit(self):
            return None

        async def refresh(self, obj):
            del obj
            return None

        async def delete(self, obj):
            del obj
            return None

    return DummyAsyncSession()


@pytest.fixture
def test_user():
    return User(
        id=uuid4(),
        clerk_id=f"clerk_{uuid4()}",
        email=f"user_{uuid4()}@example.com",
        tier=UserTier.free,
    )


@pytest.fixture
def create_comic_factory():
    def create_comic(*, user_id, status: ComicStatus = ComicStatus.pending, title: str = "Test Comic", pages_count: int = 4):
        return Comic(
            id=uuid4(),
            user_id=user_id,
            title=title,
            status=status,
            pages_count=pages_count,
            style="manga",
            story_prompt="A hero journey prompt",
            created_at=datetime.now(timezone.utc),
        )

    return create_comic


@pytest.fixture
def user_claims_factory():
    def create_claims(*, clerk_id: str = "user_123", email: str = "user@example.com", tier: str = "free"):
        return {"sub": clerk_id, "email": email, "tier": tier}

    return create_claims


@pytest.fixture
def simple_user_factory():
    def create_user(*, user_id=None):
        return SimpleNamespace(id=user_id or uuid4())

    return create_user
