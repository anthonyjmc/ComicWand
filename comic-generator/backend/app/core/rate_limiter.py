"""Redis-based sliding window rate limiting for authenticated users."""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.security import get_current_user


@dataclass
class RateLimitResult:
    """Computed rate limit state for request metadata."""

    limit: int
    remaining: int
    reset_epoch_seconds: int


class RateLimiter:
    """Rate limiter implementing sliding window with Redis sorted sets."""

    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.redis = redis_client
        self.settings = settings

    async def check(self, *, user_id: str, action: str, limit: int, window_seconds: int) -> RateLimitResult:
        """Check a rate limit and return remaining quota information."""
        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (window_seconds * 1000)
        key = f"rate_limit:{action}:{user_id}:{window_seconds}"

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start_ms)
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.zcard(key)
            pipe.pexpire(key, window_seconds * 1000)
            _, _, current_count, _ = await pipe.execute()

        used = int(current_count)
        remaining = max(limit - used, 0)
        reset_epoch = int((now_ms + (window_seconds * 1000)) / 1000)

        if used > limit:
            retry_after = max(int((window_seconds * 1000 - (now_ms - window_start_ms)) / 1000), 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action}. Retry at unix {reset_epoch}.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_epoch),
                },
            )

        return RateLimitResult(limit=limit, remaining=remaining, reset_epoch_seconds=reset_epoch)


def _attach_rate_headers(response: Response, result: RateLimitResult) -> None:
    """Attach rate limit headers to outgoing response."""
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(result.reset_epoch_seconds)


async def check_rate_limit(
    request: Request,
    response: Response,
    action: str = "api",
    user: dict = Depends(get_current_user),
) -> None:
    """FastAPI dependency that enforces user-based request and comic limits."""
    settings = get_settings()
    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    limiter = RateLimiter(redis_client=redis_client, settings=settings)

    user_id = str(user.get("sub", ""))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to identify authenticated user")

    tier = str(user.get("tier", "free")).lower()
    limits = settings.get_tier_limits(tier)

    minute_result = await limiter.check(
        user_id=user_id,
        action=f"{action}:minute",
        limit=limits["per_minute"],
        window_seconds=60,
    )
    await limiter.check(
        user_id=user_id,
        action=f"{action}:hour",
        limit=limits["per_hour"],
        window_seconds=3600,
    )

    if action == "comic_generation":
        await limiter.check(
            user_id=user_id,
            action=f"{action}:day",
            limit=limits["per_day_comics"],
            window_seconds=86400,
        )

    _attach_rate_headers(response, minute_result)
    request.state.rate_limit = minute_result
