import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border border-transparent px-2 py-0.5 font-mono text-xs font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:ring-[3px] focus-visible:ring-[#F7931A]/50 [&>svg]:pointer-events-none [&>svg]:size-3',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-r from-[#EA580C] to-[#F7931A] text-white shadow-[0_0_12px_-2px_rgba(247,147,26,0.5)] [a&]:hover:shadow-[0_0_20px_-2px_rgba(247,147,26,0.6)]',
        secondary: 'border border-white/10 bg-white/5 text-[#94A3B8] [a&]:hover:bg-white/10',
        destructive:
          'bg-[#EF4444] text-white shadow-[0_0_10px_-2px_rgba(239,68,68,0.5)] [a&]:hover:bg-[#EF4444]/90',
        warning:
          'border border-[#FFD600]/30 bg-[#FFD600]/15 text-[#FFD600] [a&]:hover:bg-[#FFD600]/25',
        outline: 'border-border text-muted-foreground [a&]:hover:border-white/30',
        ghost: '[a&]:hover:bg-white/10 [a&]:hover:text-[#F7931A]',
        link: 'text-[#F7931A] underline-offset-4 [a&]:hover:underline',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Badge({
  className,
  variant = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : 'span'

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
