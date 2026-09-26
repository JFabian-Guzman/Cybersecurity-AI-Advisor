import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { ScanListResponse } from '../types/scan'

export async function getScansByRepository(
  repositoryId: string,
  limit: number,
  offset: number,
): Promise<ScanListResponse> {
  const { data } = await apiClient.get<ScanListResponse>(
    `/api/repositories/${repositoryId}/scans`,
    {
      params: { limit, offset },
    },
  )
  return data
}

export const useScansByRepositoryQuery = (
  repositoryId: string,
  limit: number,
  offset: number,
  enabled = true,
) => {
  return useQuery({
    queryKey: ['scans', 'by-repository', repositoryId, limit, offset],
    queryFn: () => getScansByRepository(repositoryId, limit, offset),
    enabled,
    placeholderData: keepPreviousData,
  })
}
