# ComicWand Frontend

Next.js 14 App Router web client for ComicWand.

## Requirements

- Node.js 20+
- npm 9+

## Setup

From `comic-generator/frontend`:

1. Install dependencies:
   - `npm ci`
2. Create env file:
   - Windows: `copy .env.example .env.local`
3. Fill env values in `.env.local`:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - `CLERK_SECRET_KEY`
   - `NEXT_PUBLIC_API_URL` (for local backend: `http://localhost:8000`)
   - `CLERK_WEBHOOK_SECRET` (needed if handling Clerk webhooks in this app context)

## Run Dev Server

- `npm run dev`

App URL:
- `http://localhost:3000`

## Quality Checks

- Lint: `npm run lint`
- Types: `npx tsc --noEmit`

## Build

- `npm run build`
- `npm run start`
