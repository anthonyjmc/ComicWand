export class RateLimitError extends Error {
  retryAfter: number
  statusCode: number

  constructor(message: string, retryAfter: number) {
    super(message)
    this.name = 'RateLimitError'
    this.retryAfter = retryAfter
    this.statusCode = 429
  }
}

export class ApiError extends Error {
  statusCode: number

  constructor(message: string, statusCode: number) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
  }
}

function getHoursUntilReset(retryAfter: number): number {
  return Math.max(1, Math.ceil(retryAfter / 3600))
}

export function handleApiError(error: unknown): string {
  if (error instanceof RateLimitError) return `You've reached your daily limit. Resets in ${getHoursUntilReset(error.retryAfter)} hours.`

  if (error instanceof ApiError) {
    if (error.statusCode === 413) return 'Image file is too large. Maximum size is 10MB.'
    if (error.statusCode === 400) return error.message
    if (error.statusCode === 500) return 'Something went wrong. Please try again.'
    return error.message
  }

  if (error instanceof Error && error.message.toLowerCase().includes('network')) return 'Connection error. Check your internet.'

  return 'Something went wrong. Please try again.'
}
