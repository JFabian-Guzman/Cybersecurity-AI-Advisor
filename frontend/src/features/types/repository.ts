import type { ScanState } from './scan'

export interface Repository {
  id: string
  name: string
  source_type: string
  source_ref: string
  last_scan_status: ScanState | null
}

export interface RepositoryListResponse {
  items: Repository[]
  total: number
}
