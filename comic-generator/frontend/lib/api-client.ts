import { ApiError, RateLimitError } from '@/lib/errors'
import type { ComicListResponse, ComicPagesResponse, ComicStatusResponse, CreateComicResponse } from '@/lib/types'

interface RequestArgs {
  path: string
  method?: 'GET' | 'POST' | 'DELETE'
  body?: BodyInit
}

interface ApiClientArgs {
  getToken: () => Promise<string | null>
}

const API_TIMEOUT_MS = 30_000

export class ApiClient {
  private baseUrl: string
  private getToken: () => Promise<string | null>

  constructor({ getToken }: ApiClientArgs) {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL
    if (!baseUrl) throw new Error('NEXT_PUBLIC_API_URL is not configured')
    this.baseUrl = baseUrl
    this.getToken = getToken
  }

  private async getHeaders(isFormData: boolean): Promise<HeadersInit> {
    const token = await this.getToken()
    const headers: HeadersInit = {}
    if (!isFormData) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`
    return headers
  }

  private async request<T>({ path, method = 'GET', body }: RequestArgs): Promise<T> {
    const isFormData = body instanceof FormData
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS)
    let attempt = 0

    while (attempt < 3) {
      attempt += 1

      try {
        const response = await fetch(`${this.baseUrl}${path}`, {
          method,
          headers: await this.getHeaders(isFormData),
          body,
          signal: controller.signal,
        })

        if (response.status === 401) {
          if (typeof window !== 'undefined') window.location.href = '/sign-in'
          throw new ApiError('Please sign in to continue.', 401)
        }

        if (response.status === 429) {
          const retryAfter = Number(response.headers.get('Retry-After') ?? '3600')
          const payload = await response.json().catch(() => null)
          throw new RateLimitError(payload?.detail ?? 'Daily limit reached.', retryAfter)
        }

        if (!response.ok) {
          const payload = await response.json().catch(() => null)
          const detail = payload?.detail ?? 'Request failed.'
          if (response.status >= 500 && attempt < 3) {
            await new Promise((resolve) => setTimeout(resolve, 500 * 2 ** (attempt - 1)))
            continue
          }
          throw new ApiError(detail, response.status)
        }

        clearTimeout(timeout)
        if (response.status === 204) return undefined as T
        return (await response.json()) as T
      } catch (error) {
        if (error instanceof ApiError || error instanceof RateLimitError) throw error
        if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('Request timeout. Please try again.', 408)
        if (attempt >= 3) throw new Error('Network error')
        await new Promise((resolve) => setTimeout(resolve, 500 * 2 ** (attempt - 1)))
      }
    }

    clearTimeout(timeout)
    throw new Error('Network error')
  }

  async createComic(data: FormData): Promise<CreateComicResponse> {
    return this.request<CreateComicResponse>({ path: '/api/v1/comics/create', method: 'POST', body: data })
  }

  async getComicStatus(id: string): Promise<ComicStatusResponse> {
    return this.request<ComicStatusResponse>({ path: `/api/v1/comics/${id}/status` })
  }

  async listComics(page: number): Promise<ComicListResponse> {
    const limit = 20
    const offset = Math.max(0, (page - 1) * limit)
    return this.request<ComicListResponse>({ path: `/api/v1/comics?limit=${limit}&offset=${offset}` })
  }

  async deleteComic(id: string): Promise<void> {
    return this.request<void>({ path: `/api/v1/comics/${id}`, method: 'DELETE' })
  }

  async getComicPages(id: string): Promise<ComicPagesResponse> {
    const items = await this.request<ComicPagesResponse['items']>({ path: `/api/v1/comics/${id}/pages` })
    return { items }
  }
}
