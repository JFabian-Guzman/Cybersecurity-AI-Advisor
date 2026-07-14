import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'flex h-12 w-full min-w-0 rounded-lg border-b-2 border-white/20 bg-black/50 px-4 py-2 text-sm text-white outline-none transition-[border-color,box-shadow] duration-200 placeholder:text-white/30 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:border-[#F7931A] focus-visible:shadow-[0_10px_20px_-10px_rgba(247,147,26,0.3)]',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
