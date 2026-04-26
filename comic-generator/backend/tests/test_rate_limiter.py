from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

from app.core.rate_limiter import RateLimiter, _attach_rate_headers


@pytest.mark.asyncio
async def test_sliding_window_respects_limit(redis_mock, monkeypatch):
    limiter = RateLimiter(redis_client=redis_mock, settings=SimpleNamespace())
    monkeypatch.setattr("app.core.rate_limiter.time.time", lambda: 1.0)

    for _ in range(5):
        result = await limiter.check(user_id="user-a", action="comic_generation:day", limit=5, window_seconds=86400)
        assert result.remaining >= 0

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check(user_id="user-a", action="comic_generation:day", limit=5, window_seconds=86400)

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_headers_are_attached(redis_mock, monkeypatch):
    limiter = RateLimiter(redis_client=redis_mock, settings=SimpleNamespace())
    monkeypatch.setattr("app.core.rate_limiter.time.time", lambda: 10.0)

    result = await limiter.check(user_id="user-b", action="api:minute", limit=20, window_seconds=60)
    response = Response()
    _attach_rate_headers(response, result)

    assert response.headers["X-RateLimit-Limit"] == "20"
    assert response.headers["X-RateLimit-Remaining"] == "19"
    assert response.headers["X-RateLimit-Reset"].isdigit()


@pytest.mark.asyncio
async def test_returns_429_and_headers_when_exceeded(redis_mock, monkeypatch):
    limiter = RateLimiter(redis_client=redis_mock, settings=SimpleNamespace())
    monkeypatch.setattr("app.core.rate_limiter.time.time", lambda: 5.0)

    await limiter.check(user_id="user-c", action="comic_generation:day", limit=1, window_seconds=86400)
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check(user_id="user-c", action="comic_generation:day", limit=1, window_seconds=86400)

    exc = exc_info.value
    assert exc.status_code == 429
    assert exc.headers is not None
    assert exc.headers["X-RateLimit-Limit"] == "1"
    assert exc.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in exc.headers


@pytest.mark.asyncio
async def test_limit_resets_after_window(redis_mock, monkeypatch):
    limiter = RateLimiter(redis_client=redis_mock, settings=SimpleNamespace())
    timestamps = iter([0.0, 1.0, 12.0])
    monkeypatch.setattr("app.core.rate_limiter.time.time", lambda: next(timestamps))

    await limiter.check(user_id="user-d", action="api:minute", limit=1, window_seconds=10)
    with pytest.raises(HTTPException):
        await limiter.check(user_id="user-d", action="api:minute", limit=1, window_seconds=10)

    result = await limiter.check(user_id="user-d", action="api:minute", limit=1, window_seconds=10)
    assert result.remaining == 0
