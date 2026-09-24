import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { RepositoryListResponse } from '../types/repository'

export async function getRepositoryByUser(
  user_id: string,
  limit: number,
  offset: number,
): Promise<RepositoryListResponse> {
  const { data } = await apiClient.get<RepositoryListResponse>('/api/repositories', {
    params: { user_id, limit, offset }
  })
  return data
}

export const useRepositoryByUserQuery = (user_id: string, limit: number, offset: number) => {
  return useQuery({
    queryKey: ['repositories', user_id, limit, offset],
    queryFn: () => getRepositoryByUser(user_id, limit, offset),
  })
}
