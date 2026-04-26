'use client'

import { useEffect, useMemo, useState } from 'react'
import { Progress } from '@/components/ui/progress'
import { useApiClient } from '@/lib/use-api-client'
import type { ComicStatusResponse } from '@/lib/types'

interface GenerationProgressProps {
  comicId: string
  totalPages: number
  onCompleted?: (payload: ComicStatusResponse) => void
  onFailed?: (payload: ComicStatusResponse) => void
}

export function GenerationProgress({ comicId, totalPages, onCompleted, onFailed }: GenerationProgressProps) {
  const apiClient = useApiClient()
  const [status, setStatus] = useState<ComicStatusResponse | null>(null)

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    let isMounted = true

    async function pollStatus() {
      const payload = await apiClient.getComicStatus(comicId)
      if (!isMounted) return
      setStatus(payload)
      if (payload.status === 'completed') onCompleted?.(payload)
      if (payload.status === 'failed') onFailed?.(payload)
      if (payload.status === 'completed' || payload.status === 'failed') if (interval) clearInterval(interval)
    }

    pollStatus()
    interval = setInterval(pollStatus, 3000)

    return () => {
      isMounted = false
      if (interval) clearInterval(interval)
    }
  }, [apiClient, comicId, onCompleted, onFailed])

  const progress = status?.progress ?? 0
  const page = Math.max(1, Math.ceil((Math.max(progress, 30) - 30) / 60 * totalPages))
  const remainingMinutes = Math.max(1, Math.ceil((100 - progress) * 0.08))

  const statusMessage = useMemo(() => {
    if (progress <= 10) return 'Writing your story script...'
    if (progress <= 30) return 'Setting up the visual style...'
    if (progress <= 90) return `Drawing page ${Math.min(page, totalPages)} of ${totalPages}...`
    return 'Assembling your comic book...'
  }, [page, progress, totalPages])

  return (
    <div className='space-y-4 rounded-lg border border-slate-700 bg-slate-900/70 p-4'>
      <p className='text-sm font-medium'>{statusMessage}</p>
      <Progress value={progress} className='h-3' />
      <p className='text-xs text-slate-300'>{progress}% completed • ~{remainingMinutes} min remaining</p>
      <div className='grid grid-cols-4 gap-2'>
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className={`h-10 rounded ${index < Math.ceil(progress / 13) ? 'bg-primary/30' : 'bg-slate-800'} transition-colors`} />
        ))}
      </div>
    </div>
  )
}
