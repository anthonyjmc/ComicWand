'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogPortal = DialogPrimitive.Portal

export function DialogContent({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPortal>
      <DialogPrimitive.Overlay className='fixed inset-0 z-40 bg-black/70' />
      <DialogPrimitive.Content
        className={cn('fixed left-1/2 top-1/2 z-50 w-[95vw] max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-slate-950 p-4', className)}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className='absolute right-3 top-3 rounded-sm p-1 hover:bg-slate-800' aria-label='Close dialog'>
          <X className='h-4 w-4' />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPortal>
  )
}
