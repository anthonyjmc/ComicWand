export interface CreateComicResponse {
  comic_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  estimated_minutes: number
}

export interface ComicStatusResponse {
  comic_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number | null
  pdf_url?: string | null
  error_message?: string | null
}

export interface ComicListItem {
  id: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  pages_count: number
  style: string
  created_at: string
  pdf_url?: string | null
}

export interface ComicListResponse {
  items: ComicListItem[]
  limit: number
  offset: number
  total: number
}

export interface ComicPage {
  page_number: number
  image_url: string
}

export interface ComicPagesResponse {
  items: ComicPage[]
}
