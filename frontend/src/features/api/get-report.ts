import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { ScanReport } from '../types/report'

export async function getReport(scanId: string): Promise<ScanReport> {
  const { data } = await apiClient.get<ScanReport>(`/api/scans/${scanId}/report`)
  return data
}

export const useReportQuery = (scanId: string) => {
  return useQuery({
    queryKey: ['report', scanId],
    queryFn: () => getReport(scanId),
  })
}
