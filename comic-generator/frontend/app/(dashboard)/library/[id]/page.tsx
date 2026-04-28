'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useApiClient } from '@/lib/use-api-client'
import type { ComicPage } from '@/lib/types'

export default function ComicLibraryPage() {
  const params = useParams<{ id: string }>()
  const apiClient = useApiClient()
  const [pages, setPages] = useState<ComicPage[]>([])
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  useEffect(() => {
    async function loadPages() {
      if (!params.id) return
      const statusPayload = await apiClient.getComicStatus(params.id)
      setPdfUrl(statusPayload.pdf_url ?? null)
      const payload = await apiClient.getComicPages(params.id)
      setPages(payload.items)
    }
    loadPages()
  }, [apiClient, params.id])

  const activePage = useMemo(() => {
    if (activeIndex === null) return null
    return pages[activeIndex] ?? null
  }, [activeIndex, pages])

  return (
    <main className='mx-auto min-h-screen max-w-6xl space-y-6 px-4 py-6 sm:px-6'>
      <header className='flex items-center justify-between'>
        <h1 className='text-2xl font-semibold'>Comic Viewer</h1>
        {pdfUrl ? (
          <a href={pdfUrl} target='_blank' rel='noreferrer'>
            <Button aria-label='Download PDF'>Download PDF</Button>
          </a>
        ) : null}
      </header>

      <section className='grid grid-cols-2 gap-4 lg:grid-cols-3'>
        {pages.map((page, index) => (
          <article key={page.page_number} className='space-y-2 rounded-lg border border-slate-700 p-3'>
            <button type='button' className='block w-full' onClick={() => setActiveIndex(index)} aria-label={`Open page ${page.page_number}`}>
              <div className='relative h-56 w-full overflow-hidden rounded'>
                <Image
                  src={page.image_url}
                  alt={`Page ${page.page_number}`}
                  className='object-cover'
                  fill
                  sizes='(max-width: 1024px) 50vw, 33vw'
                  unoptimized
                />
              </div>
            </button>
            <div className='flex items-center justify-between'>
              <p className='text-sm'>Page {page.page_number}</p>
              <a href={page.image_url} download target='_blank' rel='noreferrer'>
                <Button size='sm' variant='outline' aria-label={`Download page ${page.page_number}`}>
                  Download
                </Button>
              </a>
            </div>
          </article>
        ))}
      </section>

      <Dialog open={activeIndex !== null} onOpenChange={(open) => !open && setActiveIndex(null)}>
        <DialogContent>
          {activePage ? (
            <div className='space-y-4'>
              <div className='relative h-[80vh] w-full overflow-hidden rounded'>
                <Image
                  src={activePage.image_url}
                  alt={`Page ${activePage.page_number} full view`}
                  className='object-cover'
                  fill
                  sizes='100vw'
                  unoptimized
                />
              </div>
              <div className='flex justify-between'>
                <Button variant='secondary' onClick={() => setActiveIndex((current) => (current && current > 0 ? current - 1 : current))} aria-label='Previous page'>
                  Previous
                </Button>
                <Button variant='secondary' onClick={() => setActiveIndex((current) => (current !== null && current < pages.length - 1 ? current + 1 : current))} aria-label='Next page'>
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </main>
  )
}
