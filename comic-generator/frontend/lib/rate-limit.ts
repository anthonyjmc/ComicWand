/**
 * Shared rate limit helper for frontend UI messaging.
 */

export interface RateLimitMetadata {
  limit: number
  remaining: number
  reset: number
}

export function parseRateLimitHeaders(headers: Headers): RateLimitMetadata {
  const limit = Number(headers.get('x-ratelimit-limit') ?? '0')
  const remaining = Number(headers.get('x-ratelimit-remaining') ?? '0')
  const reset = Number(headers.get('x-ratelimit-reset') ?? '0')
  return { limit, remaining, reset }
}
