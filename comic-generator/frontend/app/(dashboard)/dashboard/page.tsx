'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { ComicCard } from '@/components/comic/ComicCard'
import { Button } from '@/components/ui/button'
import { handleApiError } from '@/lib/errors'
import { useApiClient } from '@/lib/use-api-client'
import type { ComicListItem } from '@/lib/types'

export default function DashboardPage() {
  const apiClient = useApiClient()
  const [comics, setComics] = useState<ComicListItem[]>([])
  const [progressMap, setProgressMap] = useState<Record<string, number>>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalComics, setTotalComics] = useState(0)
  const requestSequenceRef = useRef(0)

  const totalPages = useMemo(() => Math.max(1, Math.ceil(totalComics / pageSize)), [pageSize, totalComics])

  const loadComics = useCallback(async (page: number) => {
    const requestId = ++requestSequenceRef.current
    try {
      const payload = await apiClient.listComics(page)
      if (requestSequenceRef.current !== requestId) return
      setComics(payload.items)
      setTotalComics(payload.total)
      setPageSize(payload.limit)
    } catch (error) {
      toast.error(handleApiError(error))
    }
  }, [apiClient])

  useEffect(() => {
    loadComics(currentPage)
  }, [currentPage, loadComics])

  useEffect(() => {
    const processing = comics.filter((comic) => comic.status === 'processing')
    if (!processing.length) return
    const interval = setInterval(async () => {
      const updates = await Promise.all(processing.map((comic) => apiClient.getComicStatus(comic.id).catch(() => null)))
      const nextMap: Record<string, number> = {}
      let shouldRefreshList = false
      for (const update of updates) {
        if (!update) continue
        nextMap[update.comic_id] = update.progress ?? 0
        if (update.status === 'completed' || update.status === 'failed') shouldRefreshList = true
      }
      setProgressMap((current) => ({ ...current, ...nextMap }))
      if (shouldRefreshList) loadComics(currentPage)
    }, 6000)
    return () => clearInterval(interval)
  }, [apiClient, comics, currentPage, loadComics])

  async function handleDelete(comicId: string) {
    try {
      await apiClient.deleteComic(comicId)
      toast.success('Comic deleted')
      const nextTotal = Math.max(0, totalComics - 1)
      const nextTotalPages = Math.max(1, Math.ceil(nextTotal / pageSize))
      const nextPage = Math.min(currentPage, nextTotalPages)
      setCurrentPage(nextPage)
      await loadComics(nextPage)
    } catch (error) {
      toast.error(handleApiError(error))
    }
  }

  async function handleRetry(comicId: string) {
    const selectedComic = comics.find((comic) => comic.id === comicId)
    if (!selectedComic) return
    const formData = new FormData()
    formData.append('title', selectedComic.title)
    formData.append('story_prompt', 'Please regenerate this comic with the same direction.')
    formData.append('pages', String(selectedComic.pages_count))
    formData.append('style', selectedComic.style)
    try {
      await apiClient.createComic(formData)
      toast.success('Retry started')
      await loadComics(currentPage)
    } catch (error) {
      toast.error(handleApiError(error))
    }
  }

  return (
    <main className='mx-auto min-h-screen max-w-6xl space-y-6 px-4 py-6 sm:px-6'>
      <header className='flex items-center justify-between'>
        <h1 className='text-2xl font-semibold'>My Comics</h1>
        <Link href='/create'>
          <Button aria-label='Create a new comic'>Create New</Button>
        </Link>
      </header>

      <section className='rounded-xl border border-slate-700 bg-slate-900/60 p-4'>
        <p className='text-sm text-slate-200'>{totalComics} comics in your library</p>
      </section>

      <section className='flex items-center justify-end'>
        <div className='flex items-center gap-3'>
          <Button variant='outline' size='sm' disabled={currentPage <= 1} onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}>
            {'<'}
          </Button>
          <span className='min-w-8 rounded-md bg-yellow-400 px-2 py-1 text-center text-sm font-semibold text-slate-900'>{currentPage}</span>
          <Button variant='outline' size='sm' disabled={currentPage >= totalPages} onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}>
            {'>'}
          </Button>
        </div>
      </section>

      <section className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3'>
        {comics.map((comic) => (
          <ComicCard key={comic.id} comic={comic} progress={progressMap[comic.id] ?? 0} onDelete={handleDelete} onRetry={handleRetry} />
        ))}
      </section>
    </main>
  )
}
