import { useMutation } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { Scan } from './get-scan'

export async function retryScan(scanId: string): Promise<Scan> {
  const { data } = await apiClient.post<Scan>(`/api/scans/${scanId}/retry`)
  return data
}

export function useRetryScanMutation(scanId: string) {
  return useMutation({
    mutationFn: () => retryScan(scanId),
  })
}
