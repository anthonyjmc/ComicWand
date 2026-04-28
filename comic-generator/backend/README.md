# ComicWand Backend

FastAPI API, auth/webhook handling, comic orchestration, and Celery worker pipeline.

## Requirements

- Python 3.11+
- PostgreSQL
- Redis

## Setup

From `comic-generator/backend`:

1. Create virtual environment:
   - Windows PowerShell: `python -m venv .venv`
2. Activate:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Create env file:
   - Windows: `copy .env.example .env`
5. Fill `.env` values (database, redis, Clerk, R2, AI providers)
6. Run migrations:
   - `alembic upgrade head`

## Run API

- `uvicorn app.main:app --reload --port 8000`

## Run Worker

In a second terminal (same activated env):

- `celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2`

## Optional Monitoring (Flower)

- `celery -A app.workers.celery_app.celery_app flower --port=5555`

If exposed beyond localhost, protect it with auth and network restrictions.

## Health Endpoint

- Liveness: `GET /api/v1/health`
- App status: `GET /health`
