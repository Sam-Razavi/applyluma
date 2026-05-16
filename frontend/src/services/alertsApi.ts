import client from '../api/client'

export interface AlertPreferences {
  id: string
  user_id: string
  enabled: boolean
  score_threshold: number
  frequency: 'daily' | 'weekly'
  last_sent_at: string | null
  created_at: string
  updated_at: string
}

export interface AlertPreferencesUpdate {
  enabled?: boolean
  score_threshold?: number
  frequency?: 'daily' | 'weekly'
}

export function getPreferences(): Promise<AlertPreferences> {
  return client.get<AlertPreferences>('/api/v1/me/alert-preferences').then((r) => r.data)
}

export function updatePreferences(payload: AlertPreferencesUpdate): Promise<AlertPreferences> {
  return client
    .patch<AlertPreferences>('/api/v1/me/alert-preferences', payload)
    .then((r) => r.data)
}
