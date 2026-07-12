import { AxiosError } from 'axios'

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}
