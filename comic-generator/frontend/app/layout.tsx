import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { ClerkProvider } from '@clerk/nextjs'
import { Bangers, Inter } from 'next/font/google'
import { Toaster } from 'sonner'
import './globals.css'

interface RootLayoutProps {
  children: ReactNode
}

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })
const bangers = Bangers({ subsets: ['latin'], weight: '400', variable: '--font-comic' })

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
      <body className={`${inter.variable} ${bangers.variable} font-sans`}>
        <ClerkProvider>
          {children}
          <Toaster richColors position='top-right' />
        </ClerkProvider>
      </body>
    </html>
  )
}
