import { isAxiosError } from 'axios'

export function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  if (error instanceof Error) return error.message
  return 'Unknown error'
}
