'use client'

import { formatDistanceToNow } from 'date-fns'
import Link from 'next/link'
import Image from 'next/image'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import type { ComicListItem } from '@/lib/types'

interface ComicCardProps {
  comic: ComicListItem
  progress?: number
  onDelete: (comicId: string) => Promise<void>
  onRetry: (comicId: string) => Promise<void>
}

export function ComicCard({ comic, progress = 0, onDelete, onRetry }: ComicCardProps) {
  const statusVariant = comic.status === 'pending' ? 'yellow' : comic.status === 'processing' ? 'blue' : comic.status === 'completed' ? 'green' : 'red'
  const relativeDate = formatDistanceToNow(new Date(comic.created_at), { addSuffix: true })

  return (
    <Card className='overflow-hidden'>
      <CardContent className='space-y-4 p-4'>
        {comic.status === 'pending' || comic.status === 'processing' ? (
          <Skeleton className='h-40 w-full' />
        ) : (
          <Image src={comic.pdf_url ?? '/sample-1.svg'} alt={`${comic.title} cover`} className='h-40 w-full rounded-lg object-cover' width={640} height={360} unoptimized />
        )}

        <div className='space-y-2'>
          <div className='flex items-center justify-between gap-2'>
            <h3 className='line-clamp-1 font-semibold'>{comic.title}</h3>
            <Badge variant={statusVariant}>{comic.status}</Badge>
          </div>
          <div className='flex flex-wrap gap-2 text-xs'>
            <Badge>{comic.pages_count} pages</Badge>
            <Badge>{comic.style}</Badge>
          </div>
          <p className='text-xs text-slate-400'>{relativeDate}</p>
        </div>

        {comic.status === 'processing' ? <Progress value={progress} /> : null}

        <div className='flex flex-wrap gap-2'>
          {comic.status === 'completed' && comic.pdf_url ? (
            <a href={comic.pdf_url} target='_blank' rel='noreferrer'>
              <Button size='sm' aria-label={`Download PDF for ${comic.title}`}>
                Download PDF
              </Button>
            </a>
          ) : null}
          {comic.status === 'failed' ? (
            <Button size='sm' variant='secondary' aria-label={`Retry comic generation for ${comic.title}`} onClick={() => onRetry(comic.id)}>
              Retry
            </Button>
          ) : null}
          <Link href={`/library/${comic.id}`}>
            <Button size='sm' variant='outline' aria-label={`View pages for ${comic.title}`}>
              View Pages
            </Button>
          </Link>
          <Button size='sm' variant='destructive' aria-label={`Delete ${comic.title}`} onClick={() => onDelete(comic.id)}>
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
