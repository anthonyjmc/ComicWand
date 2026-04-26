import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', {
  variants: {
    variant: {
      default: 'bg-slate-700 text-slate-100',
      yellow: 'bg-yellow-500/20 text-yellow-300',
      blue: 'bg-blue-500/20 text-blue-300',
      green: 'bg-emerald-500/20 text-emerald-300',
      red: 'bg-red-500/20 text-red-300',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, className }))} {...props} />
}
