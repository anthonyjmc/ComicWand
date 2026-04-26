"""Celery task declarations for async comic generation jobs."""

from app.workers.celery_app import celery_app


@celery_app.task(name="comic.generate")
def generate_comic_task(comic_id: str) -> dict[str, str]:
    """Background task entrypoint for generating a comic."""
    return {"comic_id": comic_id, "status": "queued"}
