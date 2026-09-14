import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'
import type { Finding } from '../types/findings'

export interface FindingsFilters {
  severities?: string[]
  categories?: string[]
}

export async function getFindings(
  scanId: string,
  filters: FindingsFilters = {},
): Promise<Finding[]> {
  const params = new URLSearchParams()
  for (const severity of filters.severities ?? []) {
    params.append('severity', severity)
  }
  for (const category of filters.categories ?? []) {
    params.append('category', category)
  }
  const queryString = params.toString()
  const url = `/api/scans/${scanId}/findings${queryString ? `?${queryString}` : ''}`
  const { data } = await apiClient.get<Finding[]>(url)
  return data
}

export const useFindingsQuery = (scanId: string, filters: FindingsFilters = {}, enabled = true) => {
  return useQuery({
    queryKey: ['findings', scanId, filters],
    queryFn: () => getFindings(scanId, filters),
    enabled,
    placeholderData: keepPreviousData,
  })
}
