import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="skeleton"
      className={cn('animate-pulse rounded-lg border border-white/10 bg-white/5', className)}
      {...props}
    />
  )
}

export { Skeleton }
