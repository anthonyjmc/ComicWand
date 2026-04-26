# Deployment Guide

## Required Environment Variables

### Backend (`backend/.env`)
- `ENVIRONMENT`: `development` or `production`
- `DATABASE_URL`: PostgreSQL DSN (`postgresql+asyncpg://...`)
- `REDIS_URL`: Redis DSN (`redis://...` or `rediss://...`)
- `REPLICATE_API_TOKEN`: from [Replicate Account API Tokens](https://replicate.com/account/api-tokens)
- `ANTHROPIC_API_KEY`: from [Anthropic Console](https://console.anthropic.com/settings/keys)
- `CLOUDFLARE_R2_BUCKET`: R2 bucket name
- `CLOUDFLARE_R2_ACCESS_KEY`: from Cloudflare R2 API tokens
- `CLOUDFLARE_R2_SECRET_KEY`: from Cloudflare R2 API tokens
- `CLOUDFLARE_R2_ENDPOINT`: `https://<account-id>.r2.cloudflarestorage.com`
- `CLERK_SECRET_KEY`: from [Clerk Dashboard](https://dashboard.clerk.com/)
- `CLERK_WEBHOOK_SECRET`: webhook signing secret from Clerk
- `ALLOWED_ORIGINS`: comma-separated frontend origins
- `ALLOWED_HOSTS`: comma-separated hostnames for trusted host middleware
- `MAX_PAGES_PER_COMIC`: default `48`
- `MAX_COMICS_PER_DAY`: default `5`
- `MAX_FILE_SIZE_MB`: default `10`

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: from Clerk dashboard
- `CLERK_SECRET_KEY`: from Clerk dashboard
- `NEXT_PUBLIC_API_URL`: backend base URL (Railway URL in production)
- `CLERK_WEBHOOK_SECRET`: used for local webhook testing helpers if required

## Railway Deployment (Backend + Worker)
1. Create a Railway project and connect this repository.
2. Add a service for `backend` and set root directory to `backend`.
3. Railway detects `backend/railway.toml` and deploys with `uvicorn`.
4. Add all backend env vars in Railway service variables.
5. Add PostgreSQL and Redis plugins/services, then wire `DATABASE_URL` and `REDIS_URL`.
6. Create a second Railway service for Celery worker using `backend/Procfile`.
7. Ensure worker service has the same env vars as API service.
8. Confirm `/health` returns healthy after deploy.

## Vercel Deployment (Frontend)
1. Import repo into Vercel and set root directory to `frontend`.
2. Set Node version to `20`.
3. Add frontend env vars in Vercel project settings.
4. Deploy and verify headers from `frontend/vercel.json` are present.
5. Set `NEXT_PUBLIC_API_URL` to Railway backend public URL.

## Clerk Webhook Setup
1. In Clerk dashboard, create webhook endpoint:
   - URL: `https://<railway-backend-domain>/api/v1/auth/webhook`
2. Subscribe to `user.created` and `user.deleted`.
3. Copy signing secret and set `CLERK_WEBHOOK_SECRET` in Railway.
4. Validate delivery in Clerk logs; backend should return `{ "status": "ok" }`.

## Cloudflare R2 CORS Setup
Configure bucket CORS to allow frontend origin and expected methods:

```json
[
  {
    "AllowedOrigins": ["https://<your-vercel-domain>"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Use signed URLs from backend for object access. Avoid permanent public object URLs for private assets.

## Production Migrations (Alembic)
From `backend`:

```bash
alembic upgrade head
```

For Railway one-off command, run the same inside the backend service shell/release command.
