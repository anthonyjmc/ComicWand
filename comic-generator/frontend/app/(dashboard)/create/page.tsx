'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { handleApiError } from '@/lib/errors'
import { useApiClient } from '@/lib/use-api-client'

type ComicStyle = 'manga' | 'western' | 'superhero' | 'cartoon' | 'noir'

export default function CreatePage() {
  const router = useRouter()
  const apiClient = useApiClient()
  const [step, setStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [title, setTitle] = useState('')
  const [storyPrompt, setStoryPrompt] = useState('')
  const [style, setStyle] = useState<ComicStyle>('manga')
  const [pages, setPages] = useState(12)
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [remainingComics, setRemainingComics] = useState(5)
  const [referenceImage, setReferenceImage] = useState<File | null>(null)

  const { getRootProps, getInputProps } = useDropzone({
    multiple: false,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] },
    onDrop: (files) => setReferenceImage(files[0] ?? null),
  })

  const estimate = useMemo(() => {
    const minutes = Math.max(5, Math.round(pages * 0.5))
    const cost = (pages * 0.042).toFixed(2)
    return `~${minutes} minutes • ~$${cost} in API costs`
  }, [pages])

  useEffect(() => {
    async function getRateLimitIndicator() {
      try {
        const payload = await apiClient.listComics(1)
        const usedToday = payload.items.filter((item) => {
          const createdDate = new Date(item.created_at)
          const now = new Date()
          return createdDate.getUTCFullYear() === now.getUTCFullYear() && createdDate.getUTCMonth() === now.getUTCMonth() && createdDate.getUTCDate() === now.getUTCDate()
        }).length
        setRemainingComics(Math.max(0, 5 - usedToday))
      } catch {
        setRemainingComics(5)
      }
    }
    getRateLimitIndicator()
  }, [apiClient])

  async function generateComic() {
    if (!acceptedTerms) {
      toast.error('Please accept the content policy terms.')
      return
    }

    setIsSubmitting(true)
    try {
      const payload = new FormData()
      payload.append('title', title)
      payload.append('story_prompt', storyPrompt)
      payload.append('style', style)
      payload.append('pages', String(pages))
      if (referenceImage) payload.append('reference_image', referenceImage)
      await apiClient.createComic(payload)
      toast.success('Comic generation started successfully')
      router.push('/dashboard')
    } catch (error) {
      toast.error(handleApiError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className='mx-auto min-h-screen max-w-4xl space-y-6 px-4 py-6 sm:px-6'>
      <h1 className='text-2xl font-semibold'>Create your comic</h1>
      <div className='space-y-2'>
        <div className='flex items-center gap-2 text-xs sm:text-sm'>
          {[1, 2, 3].map((index) => (
            <div key={index} className={`rounded-full px-3 py-1 ${step >= index ? 'bg-primary text-primary-foreground' : 'bg-slate-800 text-slate-300'}`}>
              Step {index}
            </div>
          ))}
        </div>
        <Progress value={(step / 3) * 100} />
      </div>

      {step === 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>Your Story</CardTitle>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='space-y-2'>
              <Label htmlFor='title'>Title</Label>
              <Input id='title' value={title} onChange={(event) => setTitle(event.target.value)} disabled={isSubmitting} aria-label='Comic title' />
            </div>
            <div className='space-y-2'>
              <Label htmlFor='storyPrompt'>Story Prompt</Label>
              <Textarea id='storyPrompt' value={storyPrompt} onChange={(event) => setStoryPrompt(event.target.value.slice(0, 2000))} disabled={isSubmitting} aria-label='Story prompt' rows={8} />
              <p className='text-xs text-slate-400'>{storyPrompt.length}/2000</p>
            </div>
            <div className='flex flex-wrap gap-2'>
              {promptExamples.map((example) => (
                <button key={example} type='button' className='rounded-full bg-slate-800 px-3 py-1 text-xs hover:bg-slate-700' onClick={() => setStoryPrompt(example)} aria-label='Use prompt example'>
                  {example}
                </button>
              ))}
            </div>
            <Button onClick={() => setStep(2)} disabled={isSubmitting || title.length < 5 || storyPrompt.length < 10} aria-label='Continue to style selection'>
              Continue
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {step === 2 ? (
        <Card>
          <CardHeader>
            <CardTitle>Style & Pages</CardTitle>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5'>
              {styles.map((item) => (
                <button
                  key={item.value}
                  type='button'
                  onClick={() => setStyle(item.value)}
                  className={`rounded-lg border p-3 text-left ${style === item.value ? 'border-primary bg-primary/10' : 'border-slate-700 bg-slate-900'}`}
                  aria-label={`Select ${item.label} style`}
                >
                  <Image src={item.preview} alt={`${item.label} style preview`} className='mb-2 h-24 w-full rounded object-cover' width={320} height={160} />
                  <p className='text-sm font-medium'>{item.label}</p>
                </button>
              ))}
            </div>

            <div className='space-y-2'>
              <Label htmlFor='pages'>Pages: {pages}</Label>
              <input id='pages' type='range' min={1} max={48} value={pages} onChange={(event) => setPages(Number(event.target.value))} className='w-full' aria-label='Number of pages' />
              <p className='text-sm text-slate-300'>{estimate}</p>
            </div>

            <div className='space-y-2'>
              <p className='text-sm text-slate-300'>Optional: Upload a reference photo for consistent character appearance</p>
              <div {...getRootProps()} className='cursor-pointer rounded-lg border border-dashed border-slate-600 p-6 text-center'>
                <input {...getInputProps()} aria-label='Reference image upload' />
                <p className='text-sm text-slate-300'>Drag & drop an image here, or click to select</p>
              </div>
              {referenceImage ? (
                <div className='flex items-center gap-3'>
                  <Image src={URL.createObjectURL(referenceImage)} alt='Reference preview' className='h-20 w-20 rounded object-cover' width={80} height={80} unoptimized />
                  <Button variant='destructive' size='sm' onClick={() => setReferenceImage(null)} aria-label='Remove reference image'>
                    Remove
                  </Button>
                </div>
              ) : null}
            </div>

            <div className='flex gap-2'>
              <Button variant='secondary' onClick={() => setStep(1)} aria-label='Go back to story step'>
                Back
              </Button>
              <Button onClick={() => setStep(3)} aria-label='Continue to review'>
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {step === 3 ? (
        <Card>
          <CardHeader>
            <CardTitle>Review & Generate</CardTitle>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='space-y-1 text-sm text-slate-300'>
              <p><span className='font-semibold text-slate-100'>Title:</span> {title}</p>
              <p><span className='font-semibold text-slate-100'>Style:</span> {style}</p>
              <p><span className='font-semibold text-slate-100'>Pages:</span> {pages}</p>
            </div>
            <p className='text-sm text-yellow-300'>Generation takes 5-30 minutes depending on pages</p>
            <p className='text-sm text-slate-300'>You have {remainingComics} comics remaining today</p>
            <label className='flex items-start gap-2 text-sm'>
              <input type='checkbox' checked={acceptedTerms} onChange={(event) => setAcceptedTerms(event.target.checked)} aria-label='Accept content policy terms' />
              <span>I confirm this request has no adult content and no extreme violence.</span>
            </label>
            <div className='flex gap-2'>
              <Button variant='secondary' onClick={() => setStep(2)} disabled={isSubmitting} aria-label='Go back to style step'>
                Back
              </Button>
              <Button onClick={generateComic} disabled={isSubmitting} aria-label='Generate comic now'>
                {isSubmitting ? 'Generating...' : 'Generate Comic'}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </main>
  )
}

const styles: Array<{ value: ComicStyle; label: string; preview: string }> = [
  { value: 'manga', label: 'Manga', preview: '/sample-1.svg' },
  { value: 'western', label: 'Western', preview: '/sample-2.svg' },
  { value: 'superhero', label: 'Superhero', preview: '/sample-3.svg' },
  { value: 'cartoon', label: 'Cartoon', preview: '/sample-1.svg' },
  { value: 'noir', label: 'Noir', preview: '/sample-2.svg' },
]

const promptExamples = [
  'A young detective in Tokyo discovers a conspiracy...',
  'Space pirates find an ancient alien artifact...',
  'A chef with magical powers saves her restaurant...',
]
