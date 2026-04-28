"""Celery task declarations for async comic generation jobs."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.models.comic import Comic, ComicPage, ComicStatus, PageStatus
from app.models.user import User  # noqa: F401 — ensures Comic.user relationship resolves in worker
from app.services.compositor_service import CompositorService
from app.services.image_service import ImageService
from app.services.story_service import StoryService
from app.workers.celery_app import celery_app

settings = get_settings()


@celery_app.task(name="comic.generate")
def generate_comic_task(comic_id: str, user_id: str) -> dict[str, str]:
    """Background task entrypoint for generating a comic."""
    started_at = time.perf_counter()
    logger.bind(user_id=user_id, action="comic_generate_task", duration_ms=0).info(
        "Comic generation task started comic_id={comic_id}",
        comic_id=comic_id,
    )
    try:
        result = asyncio.run(_run_generation_pipeline(comic_id=comic_id, user_id=user_id))
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.bind(user_id=user_id, action="comic_generate_task", duration_ms=duration_ms).info(
            "Comic generation task finished comic_id={comic_id}",
            comic_id=comic_id,
        )
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.bind(user_id=user_id, action="comic_generate_task", duration_ms=duration_ms).exception(
            "Comic generation task failed comic_id={comic_id} error={error_type}",
            comic_id=comic_id,
            error_type=type(exc).__name__,
        )
        raise


async def _run_generation_pipeline(comic_id: str, user_id: str) -> dict[str, str]:
    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    progress_key = f"comic:{comic_id}:progress"
    story_service = StoryService()
    image_service = ImageService()
    compositor_service = CompositorService()
    comic_uuid = UUID(comic_id)

    async with SessionFactory() as session:
        comic = await session.get(Comic, comic_uuid)
        if comic is None:
            raise ValueError(f"Comic {comic_id} not found")

        try:
            await _set_comic_status(session=session, comic=comic, status=ComicStatus.processing)
            await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=5)

            script = await story_service.generate_script(
                prompt=comic.story_prompt,
                pages=comic.pages_count,
                style=comic.style,
            )
            await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=15)

            pages_bytes: list[bytes] = []
            total_pages = len(script["pages"])

            for page_index, page in enumerate(script["pages"], start=1):
                page_number = int(page["page_number"])
                panels = page["panels"]
                scene_descriptions = [panel["scene_description"] for panel in panels]
                dialogues = [panel.get("dialogue") for panel in panels]
                camera_angles = [panel.get("camera_angle", "medium") for panel in panels]
                character_description = _build_character_description(panels=panels)

                # Sequential calls: Replicate free tier allows very low create burst; parallel gather hits 429.
                panel_urls: list[str] = []
                for scene_description in scene_descriptions:
                    panel_url = await image_service.generate_panel_image(
                        scene_description=scene_description,
                        style=comic.style,
                        reference_image_url=comic.reference_image_url,
                        character_description=character_description,
                    )
                    panel_urls.append(panel_url)

                composed_page_bytes = await compositor_service.compose_page(
                    panel_images=panel_urls,
                    dialogues=dialogues,
                    page_number=page_number,
                    style=comic.style,
                    camera_angles=camera_angles,
                )
                page_path = f"comics/{comic_id}/pages/page_{page_number}.png"
                page_public_url = await asyncio.to_thread(
                    compositor_service.storage_service.upload_file,
                    composed_page_bytes,
                    page_path,
                    "image/png",
                )
                pages_bytes.append(composed_page_bytes)

                await _upsert_comic_page(
                    session=session,
                    comic_id=comic.id,
                    page_number=page_number,
                    image_urls=panel_urls + [page_public_url],
                    dialogues=dialogues,
                )
                page_progress = 15 + int((page_index / max(total_pages, 1)) * 65)
                await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=page_progress)

            cover_url = await image_service.generate_cover(
                title=script["title"],
                style=comic.style,
                reference_image_url=comic.reference_image_url,
            )
            await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=85)
            cover_bytes = await _download_bytes(url=cover_url)

            pdf_signed_url = await compositor_service.generate_pdf(
                pages_bytes=pages_bytes,
                cover_bytes=cover_bytes,
                title=script["title"],
                comic_id=comic_id,
            )
            await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=100)

            comic.status = ComicStatus.completed
            comic.completed_at = datetime.now(timezone.utc)
            comic.pdf_url = pdf_signed_url
            comic.title = script["title"][:255]
            comic.error_message = None
            comic.generation_cost_usd = comic.generation_cost_usd + Decimal("0.0000")
            await session.commit()
            return {"comic_id": comic_id, "status": "completed", "pdf_url": pdf_signed_url}
        except Exception as exc:
            await session.rollback()
            comic.status = ComicStatus.failed
            comic.error_message = str(exc)[:4000]
            await session.commit()
            await _set_progress(redis_client=redis_client, progress_key=progress_key, progress=0)
            logger.bind(user_id=user_id, action="comic_generate_pipeline", duration_ms=0).exception(
                "Comic pipeline failed comic_id={comic_id}",
                comic_id=comic_id,
            )
            raise
        finally:
            await redis_client.aclose()


async def _set_comic_status(*, session: AsyncSession, comic: Comic, status: ComicStatus) -> None:
    comic.status = status
    await session.commit()
    await session.refresh(comic)


async def _set_progress(*, redis_client: Redis, progress_key: str, progress: int) -> None:
    safe_progress = min(max(progress, 0), 100)
    await redis_client.set(progress_key, safe_progress, ex=86400)


async def _upsert_comic_page(
    *,
    session: AsyncSession,
    comic_id: UUID,
    page_number: int,
    image_urls: list[str],
    dialogues: list[str | None],
) -> None:
    statement = select(ComicPage).where(ComicPage.comic_id == comic_id, ComicPage.page_number == page_number)
    result = await session.execute(statement)
    existing_page = result.scalar_one_or_none()

    dialogue_payload = {
        str(index + 1): dialogue
        for index, dialogue in enumerate(dialogues)
    }

    if existing_page is None:
        session.add(
            ComicPage(
                comic_id=comic_id,
                page_number=page_number,
                panel_count=4,
                image_urls=image_urls,
                dialogue=dialogue_payload,
                status=PageStatus.completed,
            )
        )
    else:
        existing_page.image_urls = image_urls
        existing_page.dialogue = dialogue_payload
        existing_page.panel_count = 4
        existing_page.status = PageStatus.completed
    await session.commit()


def _build_character_description(*, panels: list[dict]) -> str:
    has_character = any(bool(panel.get("character_present")) for panel in panels)
    if not has_character:
        return "No fixed recurring character needed in this panel."
    return "Maintain visual consistency for recurring protagonist facial features, clothing, and silhouette."


async def _download_bytes(*, url: str) -> bytes:
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
