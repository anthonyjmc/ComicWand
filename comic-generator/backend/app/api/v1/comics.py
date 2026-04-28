"""Comic generation API endpoints."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.rate_limiter import check_rate_limit
from app.core.rate_limiter import get_user_rate_limit_key
from app.core.rate_limiter import slowapi_limiter
from app.core.security import get_current_user, sanitize_prompt, validate_file_extension
from app.models.comic import Comic, ComicPage, ComicStatus
from app.models.user import User, UserTier
from app.schemas.comics import ComicListItem, ComicListResponse, ComicPageResponse, ComicResponse, ComicStatusResponse, ComicStyle, CreateComicRequest
from app.services.celery_tasks import generate_comic_task
from app.services.storage_service import StorageService
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/comics", tags=["comics"])
settings = get_settings()
storage_service = StorageService()


async def _get_or_create_user(*, session: AsyncSession, claims: dict) -> User:
    clerk_id = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip() or f"{clerk_id}@clerk.local"
    if not clerk_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    statement = select(User).where(User.clerk_id == clerk_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(clerk_id=clerk_id, email=email, tier=UserTier.free)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _extract_storage_path(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return None
    bucket_prefix = f"{settings.cloudflare_r2_bucket}/"
    if path.startswith(bucket_prefix):
        return path[len(bucket_prefix) :]
    return path


@router.post(
    "/create",
    response_model=ComicResponse,
    dependencies=[Depends(check_rate_limit)],
)
@slowapi_limiter.limit("1000/minute", key_func=get_user_rate_limit_key)
@slowapi_limiter.limit("1000/day", key_func=get_user_rate_limit_key)
async def create_comic(
    request: Request,
    response: Response,
    story_prompt: str = Form(..., min_length=10, max_length=2000),
    pages: int = Form(..., ge=1, le=48),
    style: ComicStyle = Form(...),
    title: str = Form(..., min_length=5, max_length=100),
    reference_image: UploadFile | None = File(default=None),
    user_claims: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ComicResponse:
    del request, response
    user = await _get_or_create_user(session=session, claims=user_claims)
    validated_request = CreateComicRequest(story_prompt=story_prompt, pages=pages, style=style, title=title)
    cleaned_prompt = sanitize_prompt(validated_request.story_prompt)
    cleaned_title = validated_request.title

    today = datetime.now(timezone.utc).date()
    count_statement = select(func.count(Comic.id)).where(
        and_(Comic.user_id == user.id, func.date(Comic.created_at) == today)
    )
    daily_count = int((await session.execute(count_statement)).scalar_one() or 0)
    if daily_count >= 1000:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily comic limit reached")

    processing_statement = select(Comic.id).where(and_(Comic.user_id == user.id, Comic.status == ComicStatus.processing))
    active_processing = (await session.execute(processing_statement)).scalar_one_or_none()
    if active_processing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only one processing comic is allowed")

    reference_image_url: str | None = None
    if reference_image is not None:
        validate_file_extension(reference_image.filename or "")
        image_bytes = await reference_image.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Reference image exceeds 10MB")
        object_path = f"comics/{user.id}/references/{datetime.now(timezone.utc).timestamp()}-{reference_image.filename}"
        reference_image_url = await asyncio.to_thread(
            storage_service.upload_file,
            image_bytes,
            object_path,
            reference_image.content_type or "application/octet-stream",
        )

    comic = Comic(
        user_id=user.id,
        title=cleaned_title,
        status=ComicStatus.pending,
        pages_count=validated_request.pages,
        style=validated_request.style.value,
        reference_image_url=reference_image_url,
        story_prompt=cleaned_prompt,
    )
    session.add(comic)
    await session.commit()
    await session.refresh(comic)
    generate_comic_task.delay(str(comic.id), str(user.id))

    return ComicResponse(
        comic_id=comic.id,
        status=comic.status.value,
        estimated_minutes=validated_request.pages * 0.5,
    )


@router.get(
    "/{comic_id}/status",
    response_model=ComicStatusResponse,
    dependencies=[Depends(check_rate_limit)],
)
@slowapi_limiter.limit("1000/minute", key_func=get_user_rate_limit_key)
async def get_comic_status(
    request: Request,
    response: Response,
    comic_id: UUID,
    user_claims: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ComicStatusResponse:
    del request, response
    user = await _get_or_create_user(session=session, claims=user_claims)
    result = await session.execute(select(Comic).where(Comic.id == comic_id))
    comic = result.scalar_one_or_none()
    if comic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comic not found")
    if comic.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this comic")

    payload = ComicStatusResponse(comic_id=comic.id, status=comic.status.value)
    if comic.status == ComicStatus.processing:
        redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        try:
            progress = await redis_client.get(f"comic:{comic.id}:progress")
            payload.progress = int(progress) if progress is not None else 0
        finally:
            await redis_client.aclose()
    if comic.status == ComicStatus.completed:
        pdf_path = _extract_storage_path(comic.pdf_url)
        payload.pdf_url = storage_service.get_signed_url(pdf_path, expires_in=604800) if pdf_path else comic.pdf_url
    if comic.status == ComicStatus.failed:
        payload.error_message = "Comic generation failed. Please retry."
    return payload


@router.get(
    "/",
    response_model=ComicListResponse,
    dependencies=[Depends(check_rate_limit)],
)
@slowapi_limiter.limit("1000/minute", key_func=get_user_rate_limit_key)
async def list_user_comics(
    request: Request,
    response: Response,
    limit: int = 20,
    offset: int = 0,
    user_claims: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ComicListResponse:
    del request, response
    safe_limit = min(max(limit, 1), 20)
    safe_offset = max(offset, 0)
    user = await _get_or_create_user(session=session, claims=user_claims)

    total = int(
        (await session.execute(select(func.count(Comic.id)).where(Comic.user_id == user.id))).scalar_one() or 0
    )
    result = await session.execute(
        select(Comic)
        .where(Comic.user_id == user.id)
        .order_by(desc(Comic.created_at))
        .offset(safe_offset)
        .limit(safe_limit)
    )
    comics = result.scalars().all()

    items: list[ComicListItem] = []
    for comic in comics:
        pdf_url = None
        thumbnail_url = None
        if comic.status == ComicStatus.completed:
            pdf_path = _extract_storage_path(comic.pdf_url)
            pdf_url = storage_service.get_signed_url(pdf_path, expires_in=604800) if pdf_path else comic.pdf_url
            thumbnail_result = await session.execute(
                select(ComicPage)
                .where(ComicPage.comic_id == comic.id)
                .order_by(ComicPage.page_number.asc())
                .limit(1)
            )
            thumbnail_page = thumbnail_result.scalar_one_or_none()
            if thumbnail_page and thumbnail_page.image_urls:
                thumbnail_path = _extract_storage_path(thumbnail_page.image_urls[-1])
                thumbnail_url = (
                    storage_service.get_signed_url(thumbnail_path, expires_in=604800)
                    if thumbnail_path
                    else thumbnail_page.image_urls[-1]
                )
        items.append(
            ComicListItem(
                id=comic.id,
                title=comic.title,
                status=comic.status.value,
                pages_count=comic.pages_count,
                style=comic.style,
                created_at=comic.created_at,
                pdf_url=pdf_url,
                thumbnail_url=thumbnail_url,
            )
        )
    return ComicListResponse(items=items, limit=safe_limit, offset=safe_offset, total=total)


@router.delete(
    "/{comic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(check_rate_limit)],
)
@slowapi_limiter.limit("1000/minute", key_func=get_user_rate_limit_key)
async def delete_comic(
    request: Request,
    response: Response,
    comic_id: UUID,
    user_claims: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    del request, response
    user = await _get_or_create_user(session=session, claims=user_claims)
    result = await session.execute(select(Comic).where(Comic.id == comic_id))
    comic = result.scalar_one_or_none()
    if comic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comic not found")
    if comic.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this comic")

    if comic.status == ComicStatus.processing:
        inspect_result = await asyncio.to_thread(celery_app.control.inspect().active)
        for _, tasks in (inspect_result or {}).items():
            for task in tasks or []:
                args = task.get("args") or []
                if str(comic.id) in str(args):
                    celery_app.control.revoke(task.get("id"), terminate=True)

    for file_url in [comic.reference_image_url, comic.pdf_url]:
        object_path = _extract_storage_path(file_url)
        if object_path:
            await asyncio.to_thread(storage_service.delete_file, object_path)

    await session.delete(comic)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{comic_id}/pages",
    response_model=list[ComicPageResponse],
    dependencies=[Depends(check_rate_limit)],
)
@slowapi_limiter.limit("1000/minute", key_func=get_user_rate_limit_key)
async def list_comic_pages(
    request: Request,
    response: Response,
    comic_id: UUID,
    user_claims: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ComicPageResponse]:
    del request, response
    user = await _get_or_create_user(session=session, claims=user_claims)
    result = await session.execute(select(Comic).where(Comic.id == comic_id))
    comic = result.scalar_one_or_none()
    if comic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comic not found")
    if comic.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this comic")
    if comic.status != ComicStatus.completed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Comic pages are available only when completed")

    pages_result = await session.execute(
        select(ComicPage).where(ComicPage.comic_id == comic.id).order_by(ComicPage.page_number.asc())
    )
    pages = pages_result.scalars().all()
    response_items: list[ComicPageResponse] = []
    for page in pages:
        if not page.image_urls:
            continue
        image_path = _extract_storage_path(page.image_urls[-1])
        image_url = storage_service.get_signed_url(image_path, expires_in=604800) if image_path else page.image_urls[-1]
        response_items.append(ComicPageResponse(page_number=page.page_number, image_url=image_url))
    return response_items
