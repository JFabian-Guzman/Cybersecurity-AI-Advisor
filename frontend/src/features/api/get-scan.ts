import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'

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

export async function getScan(scanId: string): Promise<Scan> {
  const { data } = await apiClient.get<Scan>(`/api/scans/${scanId}`)
  return data
}

export const useScanQuery = (scanId: string) => {
  return useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => getScan(scanId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? 2000 : false
    },
  })
}
