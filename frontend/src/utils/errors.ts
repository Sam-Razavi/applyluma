import type { AxiosError } from 'axios'

export function extractApiError(err: unknown, fallback: string): string {
  const detail = (err as AxiosError<{ detail?: string | string[] }>)?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) return detail.join(', ')
  return fallback
}
