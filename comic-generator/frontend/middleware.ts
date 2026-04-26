/**
 * Route protection and edge rate limiting middleware.
 */

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const isProtectedRoute = createRouteMatcher(['/dashboard(.*)', '/create(.*)', '/library(.*)'])
const isPublicRoute = createRouteMatcher(['/', '/sign-in(.*)', '/sign-up(.*)', '/api/webhooks(.*)'])

const edgeWindowMs = 60_000
const edgeMaxRequests = 120
const edgeCounters = new Map<string, { count: number; resetAt: number }>()

function getEdgeIdentifier(request: NextRequest): string {
  const headerUser = request.headers.get('x-clerk-user-id')
  const ipAddress = request.ip ?? 'unknown-ip'
  return headerUser ?? ipAddress
}

function enforceEdgeRateLimit(request: NextRequest): NextResponse | null {
  if (!request.nextUrl.pathname.startsWith('/api/')) return null

  const identifier = getEdgeIdentifier(request)
  const now = Date.now()
  const previous = edgeCounters.get(identifier)

  if (!previous || previous.resetAt <= now) {
    edgeCounters.set(identifier, { count: 1, resetAt: now + edgeWindowMs })
    return null
  }

  if (previous.count >= edgeMaxRequests) {
    const retryAfterSeconds = Math.ceil((previous.resetAt - now) / 1000)
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please retry later.' },
      {
        status: 429,
        headers: {
          'Retry-After': String(retryAfterSeconds),
          'X-RateLimit-Limit': String(edgeMaxRequests),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': String(Math.floor(previous.resetAt / 1000)),
        },
      }
    )
  }

  edgeCounters.set(identifier, { ...previous, count: previous.count + 1 })
  return null
}

export default clerkMiddleware(async (auth, request) => {
  const rateLimitedResponse = enforceEdgeRateLimit(request)
  if (rateLimitedResponse) return rateLimitedResponse

  if (isPublicRoute(request)) return NextResponse.next()

  if (isProtectedRoute(request)) await auth.protect()

  return NextResponse.next()
})

export const config = {
  matcher: ['/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpg|jpeg|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)', '/(api|trpc)(.*)'],
}
