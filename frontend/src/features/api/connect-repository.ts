import { apiClient } from '../../lib/api-client'

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
