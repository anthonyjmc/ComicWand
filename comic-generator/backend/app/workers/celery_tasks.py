"""Compatibility module for Celery task imports."""

from app.services.celery_tasks import generate_comic_task

__all__ = ["generate_comic_task"]
