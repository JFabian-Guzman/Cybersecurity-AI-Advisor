import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const alertVariants = cva(
  'relative w-full rounded-2xl border px-5 py-4 text-sm grid has-[>svg]:grid-cols-[calc(var(--spacing)*5)_1fr] grid-cols-[0_1fr] gap-x-3 gap-y-2 [&>svg]:col-start-1 [&>svg]:row-start-1 [&>svg]:mt-0.5 [&>svg]:size-5 [&>svg]:pointer-events-none',
  {
    variants: {
      variant: {
        default: 'border-white/10 bg-card text-card-foreground [&>svg]:text-[#F7931A]',
        destructive:
          'border-destructive/40 bg-destructive/10 text-destructive [&>svg]:text-destructive',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-title"
      className={cn('col-start-2 row-start-1 font-heading font-semibold tracking-tight', className)}
      {...props}
    />
  )
}

function AlertDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-description"
      className={cn('col-start-2 row-start-2 text-muted-foreground', className)}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
