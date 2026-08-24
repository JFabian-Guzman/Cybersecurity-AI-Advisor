import { useMutation } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import { deriveRepoName } from '@/lib/utils'

export interface ConnectedRepository {
  id: string
  name: string
  source_type: string
  source_ref: string
}

export async function connectRepository(url: string, name: string): Promise<ConnectedRepository> {
  const { data } = await apiClient.post<ConnectedRepository>('/api/repositories', { url, name })
  return data
}

export function useConnectRepositoryMutation() {
  return useMutation({
    mutationFn: async (url: string) => {
      const repository = await connectRepository(url, deriveRepoName(url))
      return repository
    },
  })
}
