import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'
import { formatDuration } from '@/lib/format-duration'

interface ScanTimerProps {
  startedAt: string | null
  finishedAt: string | null
}

export function ScanTimer({ startedAt, finishedAt }: ScanTimerProps) {
  const startedAtMs = startedAt ? new Date(startedAt).getTime() : null
  const finishedAtMs = finishedAt ? new Date(finishedAt).getTime() : null

  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (startedAtMs === null || finishedAtMs !== null) return
    const interval = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [startedAtMs, finishedAtMs])

  if (startedAtMs === null) return null

  const elapsedMs = (finishedAtMs ?? now) - startedAtMs

  return (
    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <Clock className="size-4" />
      {formatDuration(elapsedMs / 1000)}
    </span>
  )
}
