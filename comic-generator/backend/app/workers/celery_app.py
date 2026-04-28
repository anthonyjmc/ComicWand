"""Celery app factory and worker configuration."""

import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("comic_generator", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    imports=("app.workers.celery_tasks",),
)

if settings.redis_url.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
