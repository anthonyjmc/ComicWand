import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { ClerkProvider } from '@clerk/nextjs'
import { Toaster } from 'sonner'
import './globals.css'

interface RootLayoutProps {
  children: ReactNode
}

export const metadata: Metadata = {
  title: 'ComicWand - AI Comic Book Generator',
  description: 'Generate complete comic books from your story idea in minutes.',
  openGraph: {
    title: 'ComicWand - AI Comic Book Generator',
    description: 'Turn your prompts into complete comic books.',
    images: ['/og-comicwand.svg'],
  },
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang='en'>
      <body className='font-sans'>
        <ClerkProvider>
          {children}
          <Toaster richColors position='top-right' />
        </ClerkProvider>
      </body>
    </html>
  )
}
