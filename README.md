# Comic Book Generator

Production-oriented web app that generates comic books from user prompts, keeps visual consistency with reference images, and exports downloadable PDFs.

## Architecture

```text
+-------------------+        HTTPS         +-----------------------------+
| Next.js Frontend  | -------------------> | FastAPI Backend (Railway)   |
| (Vercel + Clerk)  |                      | Auth, API, Validation       |
+-------------------+                      +---------------+-------------+
        |                                                    |
        | Clerk auth session                                 | enqueue jobs
        v                                                    v
+-------------------+                                +---------------------+
| Clerk             |                                | Celery Worker       |
| Identity + JWT    |                                | image/pdf pipeline  |
+-------------------+                                +----------+----------+
                                                               |
                           +----------------------+------------+------------+
                           |                      |                         |
                           v                      v                         v
                    +-------------+       +---------------+          +--------------+
                    | PostgreSQL  |       | Redis/Upstash |          | Cloudflare R2|
                    | users/comics|       | rate/jobs     |          | assets + PDFs |
                    +-------------+       +---------------+          +--------------+
                                                               |
                                                               v
                                                   +-----------------------+
                                                   | Replicate + Claude API|
                                                   | image + story pipeline |
                                                   +-----------------------+
```

## Tech Stack
- [Next.js 14 App Router](https://nextjs.org/docs/app)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)
- [Celery](https://docs.celeryq.dev/)
- [Replicate](https://replicate.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Cloudflare R2](https://developers.cloudflare.com/r2/)
- [Clerk](https://clerk.com/docs)

## Features
- Auth with Clerk and verified backend tokens
- Prompt sanitization and content blocking
- User-based rate limiting and daily comic quotas
- Async comic generation with Celery workers
- Per-user ownership checks on comic resources
- Signed URLs for protected R2 assets
- PDF export pipeline with Pillow + FPDF2

## Quick Start

1. Open the app project folder:
   - `cd comic-generator`
2. Follow setup guides:
   - Backend: `backend/README.md`
   - Frontend: `frontend/README.md`
3. Or use the full app guide:
   - `README.md` inside `comic-generator/`

## Running All Services (Local)

From `comic-generator/`, run each in a separate terminal:

- Backend API:
  - `cd backend`
  - `uvicorn app.main:app --reload --port 8000`
- Celery worker:
  - `cd backend`
  - `celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2`
- Frontend:
  - `cd frontend`
  - `npm run dev`

## Screenshots
- `public/screenshots/home-placeholder.png`
- `public/screenshots/generator-placeholder.png`
- `public/screenshots/library-placeholder.png`

## Running Tests
- Backend:
  - `cd backend`
  - `pytest`
- With coverage:
  - `pytest --cov=app --cov-report=term-missing`
- Frontend quality checks:
  - `cd frontend`
  - `npm run lint`
  - `npx tsc --noEmit`

## Required Environment Variables
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for the full, production-ready variable list and source links.

## Known Limitations
- Character visual consistency across long runs is approximately 80% and may require retries for best output.
- Queue latency can increase during high load if worker concurrency is low.

## Estimated Usage Cost
Approximate per-comic cost (depends on page count and model settings):
- Replicate image generation: `$0.03 - $0.20`
- Claude story generation: `$0.005 - $0.04`
- Cloudflare R2 storage + egress: `< $0.01` typical per comic
- Total rough range: `$0.04 - $0.25` per comic