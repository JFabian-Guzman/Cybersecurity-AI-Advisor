const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface DbCheck {
  database: string
  select_1: number
  checked_at: string
}

export async function fetchDbCheck(): Promise<DbCheck> {
  const response = await fetch(`${API_URL}/api/db-check`)
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`)
  }
  return (await response.json()) as DbCheck
}
