'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { ComicCard } from '@/components/comic/ComicCard'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { handleApiError } from '@/lib/errors'
import { useApiClient } from '@/lib/use-api-client'
import type { ComicListItem } from '@/lib/types'

export default function DashboardPage() {
  const apiClient = useApiClient()
  const [comics, setComics] = useState<ComicListItem[]>([])
  const [progressMap, setProgressMap] = useState<Record<string, number>>({})

  const loadComics = useCallback(async () => {
    try {
      const payload = await apiClient.listComics(1)
      setComics(payload.items)
    } catch (error) {
      toast.error(handleApiError(error))
    }
  }, [apiClient])

  useEffect(() => {
    loadComics()
  }, [loadComics])

  useEffect(() => {
    const processing = comics.filter((comic) => comic.status === 'processing' || comic.status === 'pending')
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
      if (shouldRefreshList) loadComics()
    }, 3000)
    return () => clearInterval(interval)
  }, [apiClient, comics, loadComics])

  async function handleDelete(comicId: string) {
    try {
      await apiClient.deleteComic(comicId)
      toast.success('Comic deleted')
      await loadComics()
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
      await loadComics()
    } catch (error) {
      toast.error(handleApiError(error))
    }
  }

  const used = comics.length > 5 ? 5 : comics.length
  const rateProgress = useMemo(() => (used / 5) * 100, [used])

  return (
    <main className='mx-auto min-h-screen max-w-6xl space-y-6 px-4 py-6 sm:px-6'>
      <header className='flex items-center justify-between'>
        <h1 className='text-2xl font-semibold'>My Comics</h1>
        <Link href='/create'>
          <Button aria-label='Create a new comic'>Create New</Button>
        </Link>
      </header>

      <section className='space-y-2 rounded-xl border border-slate-700 bg-slate-900/60 p-4'>
        <p className='text-sm text-slate-200'>{used}/5 comics used today</p>
        <Progress value={rateProgress} />
      </section>

      <section className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3'>
        {comics.map((comic) => (
          <ComicCard key={comic.id} comic={comic} progress={progressMap[comic.id] ?? 0} onDelete={handleDelete} onRetry={handleRetry} />
        ))}
      </section>
    </main>
  )
}
