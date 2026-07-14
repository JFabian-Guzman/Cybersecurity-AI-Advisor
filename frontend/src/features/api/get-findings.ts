import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { Finding } from '../types/findings'

export async function getFindings(scanId: string): Promise<Finding[]> {
  const { data } = await apiClient.get<Finding[]>(`/api/scans/${scanId}/findings`)
  return data
}

export const useFindingsQuery = (scanId: string) => {
  return useQuery({
    queryKey: ['findings', scanId],
    queryFn: () => getFindings(scanId),
  })
}
