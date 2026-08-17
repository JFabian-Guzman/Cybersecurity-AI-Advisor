import { apiClient } from '../../lib/api-client'
import type { Scan } from './get-scan'

export async function createScan(repositoryId: string): Promise<Scan> {
  const { data } = await apiClient.post<Scan>('/api/scans', { repository_id: repositoryId })
  return data
}
