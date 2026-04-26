/**
 * Root layout for the Next.js frontend application.
 */

import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './globals.css'

interface RootLayoutProps {
  children: ReactNode
}

export const metadata: Metadata = {
  title: 'Comic Generator',
  description: 'Production-grade comic book generator platform',
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang='en'>
      <body>{children}</body>
    </html>
  )
}
