import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'

export const SCAN_POLL_TIMEOUT_MS = 5 * 60 * 1000
const SCAN_POLL_INTERVAL_MS = 2000

export type ScanState = 'queued' | 'running' | 'succeeded' | 'failed'

export interface Scan {
  id: string
  repository_id: string
  repository_name: string
  status: ScanState
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export class ScanStuckError extends Error {
  constructor() {
    super('Scan is taking longer than expected')
  }
}

export async function getScan(scanId: string): Promise<Scan> {
  const { data } = await apiClient.get<Scan>(`/api/scans/${scanId}`)
  return data
}

export function useScanQuery(scanId: string, attempt = 0) {
  const startedAtRef = useRef<number | null>(null)

  const query = useQuery({
    queryKey: ['scan', scanId, attempt],
    queryFn: async () => {
      const startedAt = startedAtRef.current ?? Date.now()
      if (Date.now() - startedAt >= SCAN_POLL_TIMEOUT_MS) {
        throw new ScanStuckError()
      }
      return getScan(scanId)
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status !== 'queued' && status !== 'running') return false
      const startedAt = startedAtRef.current ?? Date.now()
      if (Date.now() - startedAt >= SCAN_POLL_TIMEOUT_MS) return false
      return SCAN_POLL_INTERVAL_MS
    },
    retry: (failureCount, error) => !(error instanceof ScanStuckError) && failureCount < 3,
  })

  useEffect(() => {
    startedAtRef.current = Date.now()
  }, [attempt, query.data?.started_at])

  return query
}
