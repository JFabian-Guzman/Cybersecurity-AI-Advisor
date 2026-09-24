export interface Repository {
  id: string
  name: string
  source_type: string
  source_ref: string
}

export interface RepositoryListResponse {
  items: Repository[]
  total: number
}
