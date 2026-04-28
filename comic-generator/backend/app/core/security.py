"""Authentication and input sanitization utilities for API safety."""

from __future__ import annotations

import json
import re
from urllib.request import urlopen
from urllib.parse import urlparse
from html import unescape
from typing import Any

from fastapi import Header, HTTPException, Request, status
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.core.config import get_settings

TAG_RE = re.compile(r"<[^>]+>")
UNSAFE_CHAR_RE = re.compile(r"[^\w\s.,!?()'\":;\\-]")
BLOCKED_WORDS = {"hate", "terrorism", "self-harm", "nsfw-extreme"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CLERK_ISSUER_HOST_SUFFIXES = ("clerk.accounts.dev", "clerk.com")


def _is_allowed_clerk_issuer(*, issuer: str, configured_issuer: str | None) -> bool:
    parsed_issuer = urlparse(issuer)
    if parsed_issuer.scheme != "https" or not parsed_issuer.netloc:
        return False

    normalized_issuer = issuer.rstrip("/")
    if configured_issuer:
        return normalized_issuer == configured_issuer.rstrip("/")

    host = (parsed_issuer.hostname or "").lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in CLERK_ISSUER_HOST_SUFFIXES)


def verify_clerk_token(token: str) -> dict[str, Any]:
    """Verify Clerk JWT token and return claims."""
    settings = get_settings()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    clean_token = token.removeprefix("Bearer ").strip()
    if not clean_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    try:
        unverified_claims = jwt.get_unverified_claims(clean_token)
        unverified_headers = jwt.get_unverified_header(clean_token)
        issuer = str(unverified_claims.get("iss", "")).strip()
        if not _is_allowed_clerk_issuer(issuer=issuer, configured_issuer=settings.clerk_issuer):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token issuer is not allowed")
        if not unverified_claims.get("sub"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing")

        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        with urlopen(jwks_url, timeout=5) as response:
            jwks = json.loads(response.read().decode("utf-8"))

        key_id = unverified_headers.get("kid")
        if not key_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token key id is missing")

        matched_key = next((key for key in jwks.get("keys", []) if key.get("kid") == key_id), None)
        if not matched_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to match token signing key")

        public_key = jwk.construct(matched_key)
        message, encoded_signature = clean_token.rsplit(".", maxsplit=1)
        if not public_key.verify(message.encode("utf-8"), base64url_decode(encoded_signature.encode("utf-8"))):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

        decode_kwargs: dict[str, Any] = {
            "algorithms": [matched_key.get("alg", "RS256")],
            "issuer": settings.clerk_issuer.rstrip("/") if settings.clerk_issuer else issuer.rstrip("/"),
        }
        if settings.clerk_audience:
            decode_kwargs["audience"] = settings.clerk_audience

        claims = jwt.decode(clean_token, matched_key, **decode_kwargs)
        return claims
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed") from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        if settings.is_production:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unauthorized: {exc}") from exc


def sanitize_prompt(text: str) -> str:
    """Sanitize prompt text and reject unsafe or inappropriate content."""
    if not text or not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt is required")
    if len(text) > 2000:
        text = text[:2000]

    normalized_text = unescape(text)
    stripped_html = TAG_RE.sub("", normalized_text)
    cleaned = UNSAFE_CHAR_RE.sub("", stripped_html).strip()

    lowered = cleaned.lower()
    if any(word in lowered for word in BLOCKED_WORDS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt contains prohibited content",
        )
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt is empty after sanitization")
    return cleaned


def validate_file_extension(filename: str) -> str:
    """Validate uploaded file extension."""
    normalized = filename.strip().lower()
    if "." not in normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is required")
    extension = f".{normalized.split('.')[-1]}"
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type is not allowed")
    return extension


async def get_current_user(request: Request, authorization: str = Header(default="")) -> dict[str, Any]:
    """FastAPI dependency returning authenticated user claims."""
    claims = verify_clerk_token(authorization)
    request.state.user_id = str(claims.get("sub", ""))
    return claims

