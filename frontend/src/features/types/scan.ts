export type ScanState = 'queued' | 'running' | 'succeeded' | 'failed'

export interface Scan {
  id: string
  repository_id: string
  repository_name: string
  status: ScanState
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface ScanListResponse {
  items: Scan[]
  total: number
}
