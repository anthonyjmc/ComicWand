'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SignOutButton, UserButton } from '@clerk/nextjs'
import { BookOpen, LayoutDashboard, LogOut, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'

interface DashboardShellProps {
  children: ReactNode
}

interface NavItem {
  label: string
  href: string
  icon: typeof LayoutDashboard
  isActive: (pathname: string) => boolean
}

const baseNavItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    isActive: (pathname) => pathname === '/dashboard',
  },
  {
    label: 'Create Comic',
    href: '/create',
    icon: Sparkles,
    isActive: (pathname) => pathname === '/create',
  },
]

export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname()
  const currentComicHref = pathname.startsWith('/library/') ? pathname : null
  const navItems = currentComicHref
    ? [
        ...baseNavItems,
        {
          label: 'Current Comic',
          href: currentComicHref,
          icon: BookOpen,
          isActive: (currentPath: string) => currentPath.startsWith('/library/'),
        } satisfies NavItem,
      ]
    : baseNavItems

  return (
    <div className='min-h-screen bg-slate-950 text-slate-100'>
      <header className='sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur'>
        <div className='mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6'>
          <div className='flex items-center gap-3'>
            <div className='rounded-lg bg-primary/20 p-2 text-primary'>
              <Sparkles className='h-4 w-4' />
            </div>
            <div>
              <p className='font-[var(--font-comic)] text-xl leading-none text-yellow-300'>ComicWand</p>
              <p className='text-xs text-slate-400'>AI Comic Studio</p>
            </div>
          </div>
          <UserButton afterSignOutUrl='/' />
        </div>
      </header>

      <div className='mx-auto flex w-full max-w-7xl gap-6 px-4 py-6 sm:px-6'>
        <aside className='hidden w-64 shrink-0 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:block'>
          <p className='mb-3 text-xs uppercase tracking-wide text-slate-400'>Workspace</p>
          <nav className='space-y-2'>
            {navItems.map((item) => {
              const isActive = item.isActive(pathname)
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                    isActive ? 'bg-primary text-primary-foreground' : 'text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <Icon className='h-4 w-4' />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </nav>

          <div className='mt-6 border-t border-slate-800 pt-4'>
            <SignOutButton redirectUrl='/'>
              <button
                type='button'
                className='flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-slate-100'
              >
                <LogOut className='h-4 w-4' />
                <span>Logout</span>
              </button>
            </SignOutButton>
          </div>
        </aside>

        <main className='min-w-0 flex-1'>{children}</main>
      </div>
    </div>
  )
}
