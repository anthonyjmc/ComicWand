"""Auth-related endpoints wired to Clerk-backed identity."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.comic import Comic, ComicStatus
from app.models.user import User, UserTier
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
WEBHOOK_MAX_AGE_SECONDS = 300
WEBHOOK_ID_TTL_SECONDS = 900


def _verify_clerk_webhook_signature(
    *,
    payload: bytes,
    webhook_secret: str,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
) -> bool:
    secret_value = webhook_secret.removeprefix("whsec_")
    key = base64.b64decode(secret_value)
    signed_payload = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(key, signed_payload, hashlib.sha256).digest()
    expected_signature = f"v1,{base64.b64encode(digest).decode('utf-8')}"
    signatures = [item.strip() for item in svix_signature.split(" ") if item.strip()]
    return any(hmac.compare_digest(signature, expected_signature) for signature in signatures)


async def _cancel_user_active_jobs(clerk_id: str) -> None:
    inspect_result = await asyncio.to_thread(celery_app.control.inspect().active)
    for _, tasks in (inspect_result or {}).items():
        for task in tasks or []:
            if clerk_id in str(task.get("args")):
                celery_app.control.revoke(task.get("id"), terminate=True)


async def _mark_webhook_seen(*, svix_id: str) -> bool:
    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        # SET key value NX EX ttl -> returns True only if key is new.
        key = f"webhook:svix:{svix_id}"
        was_new = await redis_client.set(key, "1", ex=WEBHOOK_ID_TTL_SECONDS, nx=True)
        return bool(was_new)
    finally:
        await redis_client.aclose()


@router.post("/webhook")
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    svix_id: str = Header(default=""),
    svix_timestamp: str = Header(default=""),
    svix_signature: str = Header(default=""),
) -> dict[str, str]:
    payload = await request.body()
    if not (svix_id and svix_timestamp and svix_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing webhook signature headers")
    try:
        timestamp_seconds = int(svix_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook timestamp") from exc
    if abs(int(time.time()) - timestamp_seconds) > WEBHOOK_MAX_AGE_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook timestamp is expired")
    if not _verify_clerk_webhook_signature(
        payload=payload,
        webhook_secret=settings.clerk_webhook_secret,
        svix_id=svix_id,
        svix_timestamp=svix_timestamp,
        svix_signature=svix_signature,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    is_new_event = await _mark_webhook_seen(svix_id=svix_id)
    if not is_new_event:
        return {"status": "duplicate"}

    event = json.loads(payload.decode("utf-8"))
    event_type = str(event.get("type", ""))
    data = event.get("data", {}) or {}

    if event_type == "user.created":
        clerk_id = str(data.get("id", "")).strip()
        email_addresses = data.get("email_addresses", []) or []
        primary_email_id = data.get("primary_email_address_id")
        email = ""
        for item in email_addresses:
            if item.get("id") == primary_email_id:
                email = str(item.get("email_address", "")).strip()
        if not email and email_addresses:
            email = str(email_addresses[0].get("email_address", "")).strip()
        if clerk_id and email:
            existing = (await session.execute(select(User).where(User.clerk_id == clerk_id))).scalar_one_or_none()
            if existing is None:
                session.add(User(clerk_id=clerk_id, email=email, tier=UserTier.free))
                await session.commit()

    if event_type == "user.deleted":
        clerk_id = str(data.get("id", "")).strip()
        if clerk_id:
            user = (await session.execute(select(User).where(User.clerk_id == clerk_id))).scalar_one_or_none()
            if user is not None:
                user.clerk_id = f"deleted:{clerk_id}"
                user.email = f"deleted-{user.id}@deleted.local"
                await session.commit()
                await _cancel_user_active_jobs(clerk_id)

    return {"status": "ok"}


@router.get("/me")
async def read_current_user(user_claims: dict = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> dict:
    clerk_id = str(user_claims.get("sub", "")).strip()
    if not clerk_id:
        return {"error": "unauthorized", "message": "Invalid token"}

    user = (await session.execute(select(User).where(User.clerk_id == clerk_id))).scalar_one_or_none()
    if user is None:
        email = str(user_claims.get("email", "")).strip() or f"{clerk_id}@clerk.local"
        user = User(clerk_id=clerk_id, email=email, tier=UserTier.free)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    today = datetime.now(timezone.utc).date()
    comics_today = int(
        (
            await session.execute(
                select(func.count(Comic.id)).where(and_(Comic.user_id == user.id, func.date(Comic.created_at) == today))
            )
        ).scalar_one()
        or 0
    )
    tier_limits = settings.get_tier_limits(user.tier.value)
    daily_limit = int(tier_limits["per_day_comics"])
    remaining = max(daily_limit - comics_today, 0)
    return {
        "id": str(user.id),
        "clerk_id": user.clerk_id,
        "email": user.email,
        "tier": user.tier.value,
        "comics_generated_today": comics_today,
        "daily_limit": daily_limit,
        "comics_remaining_today": remaining,
    }
