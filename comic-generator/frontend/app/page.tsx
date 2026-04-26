import Link from 'next/link'
import Image from 'next/image'
import { SignInButton } from '@clerk/nextjs'
import { Sparkles, Palette, BookOpenText, Zap, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function HomePage() {
  return (
    <main className='mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6'>
      <header className='mb-12 flex items-center justify-between'>
        <p className='font-[var(--font-comic)] text-3xl text-yellow-300'>ComicWand</p>
        <SignInButton mode='modal'>
          <Button aria-label='Sign in to ComicWand'>Sign In</Button>
        </SignInButton>
      </header>

      <section className='space-y-6 text-center'>
        <h1 className='comic-title font-[var(--font-comic)] text-5xl text-yellow-300 sm:text-7xl'>Generate Epic Comics From One Prompt</h1>
        <p className='mx-auto max-w-2xl text-slate-200'>
          Turn your story idea into a full comic book with pages, dialogue, style consistency, and downloadable PDF.
        </p>
        <Link href='/create'>
          <Button className='text-base' size='lg' aria-label='Create your comic'>
            Create Your Comic
          </Button>
        </Link>
      </section>

      <section className='mt-12 grid grid-cols-1 gap-4 sm:grid-cols-3'>
        {['/sample-1.svg', '/sample-2.svg', '/sample-3.svg'].map((source, index) => (
          <Card key={source}>
            <CardContent className='p-0'>
              <Image src={source} alt={`Example comic preview ${index + 1}`} className='h-56 w-full rounded-xl object-cover' width={800} height={560} />
            </CardContent>
          </Card>
        ))}
      </section>

      <section className='mt-16'>
        <h2 className='mb-6 text-2xl font-semibold'>Choose Your Style</h2>
        <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5'>
          {featureStyles.map((style) => (
            <Card key={style.title}>
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
        <h2 className='mb-6 text-2xl font-semibold'>Pricing</h2>
        <Card>
          <CardHeader>
            <CardTitle>Free</CardTitle>
          </CardHeader>
          <CardContent className='text-sm text-slate-300'>5 comics/day, max 24 pages per comic</CardContent>
        </Card>
      </section>
    </main>
  )
}

const featureStyles = [
  { title: 'Manga', description: 'Dynamic framing and anime energy', icon: Sparkles },
  { title: 'Western', description: 'Classic storytelling and realism', icon: BookOpenText },
  { title: 'Superhero', description: 'Bold colors and cinematic action', icon: Zap },
  { title: 'Cartoon', description: 'Playful characters and vibrant tones', icon: Palette },
  { title: 'Noir', description: 'Moody shadows and dramatic contrast', icon: ShieldCheck },
]
