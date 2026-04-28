import Link from 'next/link'
import Image from 'next/image'
import { SignInButton } from '@clerk/nextjs'
import { ArrowRight, BookOpenText, Palette, ShieldCheck, Sparkles, Wand2, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function HomePage() {
  return (
    <main className='mx-auto min-h-screen w-full max-w-6xl px-4 py-8 sm:px-6 lg:py-10'>
      <header className='mb-10 flex items-center justify-between rounded-2xl border border-slate-800/80 bg-slate-900/60 px-4 py-3 backdrop-blur sm:px-6'>
        <p className='font-[var(--font-comic)] text-2xl text-yellow-300 sm:text-3xl'>ComicWand</p>
        <SignInButton mode='modal'>
          <Button aria-label='Sign in to ComicWand'>Sign In</Button>
        </SignInButton>
      </header>

      <section className='rounded-3xl border border-slate-800/80 bg-slate-900/50 p-6 sm:p-10'>
        <div className='grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_340px]'>
          <div>
            <div className='mb-6 inline-flex items-center gap-2 rounded-full border border-yellow-300/40 bg-yellow-300/10 px-3 py-1 text-xs text-yellow-200 sm:text-sm'>
              <Wand2 className='h-4 w-4' />
              <span>AI comic studio for creators and storytellers</span>
            </div>
            <h1 className='max-w-4xl text-balance text-4xl font-semibold leading-tight text-white sm:text-6xl'>Turn one idea into a full comic in minutes</h1>
            <p className='mt-5 max-w-3xl text-base text-slate-300 sm:text-lg'>
              ComicWand generates pages, dialogue, and consistent visual style from a single prompt. Publish, share, or export as PDF without a complex production workflow.
            </p>
            <div className='mt-8 flex flex-wrap items-center gap-3'>
              <Link href='/create'>
                <Button className='gap-2 text-base' size='lg' aria-label='Create your comic'>
                  Create my comic
                  <ArrowRight className='h-4 w-4' />
                </Button>
              </Link>
              <Link href='/dashboard'>
                <Button variant='secondary' size='lg' aria-label='Open dashboard'>
                  Open dashboard
                </Button>
              </Link>
            </div>
            <div className='mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4'>
              {heroStats.map((item) => (
                <div key={item.label} className='rounded-xl border border-slate-800/80 bg-slate-950/70 p-4'>
                  <p className='text-xl font-semibold text-white sm:text-2xl'>{item.value}</p>
                  <p className='mt-1 text-xs text-slate-400 sm:text-sm'>{item.label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className='mx-auto w-full max-w-xs rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3 shadow-2xl shadow-black/30'>
            <Image src='/sample-2.png' alt='Comic preview panel' className='h-[420px] w-full rounded-xl object-cover' width={640} height={960} priority />
          </div>
        </div>
      </section>

      <section className='mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3'>
        {['/sample-1.svg', '/sample-2.png', '/sample-3.svg'].map((source, index) => (
          <Card key={source} className='overflow-hidden border-slate-800/80 bg-slate-900/60'>
            <CardContent className='p-0'>
              <Image src={source} alt={`Example comic preview ${index + 1}`} className='h-56 w-full object-cover' width={800} height={560} />
            </CardContent>
          </Card>
        ))}
      </section>

      <section className='mt-16'>
        <h2 className='mb-2 text-2xl font-semibold sm:text-3xl'>Ready-to-use visual styles</h2>
        <p className='mb-6 max-w-2xl text-sm text-slate-400 sm:text-base'>Switch your story tone in one click while keeping character consistency and composition across pages.</p>
        <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5'>
          {featureStyles.map((style) => (
            <Card key={style.title} className='border-slate-800/80 bg-slate-900/60'>
              <CardHeader className='pb-2'>
                <style.icon className='h-5 w-5 text-yellow-300' />
                <CardTitle className='mt-2 text-base'>{style.title}</CardTitle>
              </CardHeader>
              <CardContent className='pt-0 text-sm text-slate-300'>{style.description}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className='mt-16'>
        <h2 className='mb-6 text-2xl font-semibold sm:text-3xl'>Simple flow, professional output</h2>
        <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
          {workflowSteps.map((step) => (
            <Card key={step.title} className='border-slate-800/80 bg-slate-900/60'>
              <CardHeader>
                <p className='text-xs uppercase tracking-wide text-yellow-300'>{step.eyebrow}</p>
                <CardTitle>{step.title}</CardTitle>
              </CardHeader>
              <CardContent className='text-sm text-slate-300'>{step.description}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className='mt-16'>
        <h2 className='mb-6 text-2xl font-semibold sm:text-3xl'>Starter plan</h2>
        <Card className='border-slate-800/80 bg-slate-900/60'>
          <CardHeader>
            <CardTitle>Free</CardTitle>
          </CardHeader>
          <CardContent className='space-y-3 text-sm text-slate-300'>
            {planItems.map((item) => (
              <p key={item} className='flex items-center gap-2'>
                <Sparkles className='h-4 w-4 text-yellow-300' />
                <span>{item}</span>
              </p>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className='mb-10 mt-16 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 text-center sm:p-8'>
        <h2 className='text-2xl font-semibold sm:text-3xl'>Ready to launch your first story?</h2>
        <p className='mx-auto mt-3 max-w-2xl text-slate-300'>Start free and publish your first comic today with a fast, modern workflow.</p>
        <div className='mt-6 flex justify-center'>
          <Link href='/create'>
            <Button size='lg' className='gap-2' aria-label='Start creating your first comic'>
              Get started now
              <ArrowRight className='h-4 w-4' />
            </Button>
          </Link>
        </div>
      </section>
    </main>
  )
}

const heroStats = [
  { value: '1 prompt', label: 'to start' },
  { value: '5 min', label: 'minimum estimated time' },
  { value: '48', label: 'maximum pages' },
  { value: 'PDF', label: 'direct export' },
]

const featureStyles = [
  { title: 'Manga', description: 'Dynamic framing and anime energy', icon: Sparkles },
  { title: 'Western', description: 'Classic storytelling and realism', icon: BookOpenText },
  { title: 'Superhero', description: 'Bold colors and cinematic action', icon: Zap },
  { title: 'Cartoon', description: 'Playful characters and vibrant tones', icon: Palette },
  { title: 'Noir', description: 'Moody shadows and dramatic contrast', icon: ShieldCheck },
]

const workflowSteps = [
  {
    eyebrow: 'Step 1',
    title: 'Describe your story',
    description: 'Write a short or detailed idea. We structure scenes and narrative continuity.',
  },
  {
    eyebrow: 'Step 2',
    title: 'Choose style and pages',
    description: 'Adjust visual tone, page count, and an optional reference image for consistency.',
  },
  {
    eyebrow: 'Step 3',
    title: 'Generate and share',
    description: 'Get the full comic, review results in the dashboard, and download it as PDF.',
  },
]

const planItems = ['5 comics per day', 'Up to 48 pages per comic', 'Library and real-time progress']
