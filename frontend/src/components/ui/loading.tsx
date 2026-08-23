import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

interface LoadingProps {
  label: string
  className?: string
}

function Loading({ label, className }: LoadingProps) {
  return (
    <p data-slot="loading" className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
      <Spinner />
      {label}
    </p>
  )
}

export { Loading }
