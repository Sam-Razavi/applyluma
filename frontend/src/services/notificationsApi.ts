import client from '../api/client'

export interface Notification {
  id: string
  user_id: string
  type: string
  title: string
  body: string
  related_id: string | null
  related_type: string | null
  is_read: boolean
  created_at: string
  updated_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  unread_count: number
  skip: number
  limit: number
}

export function fetchNotifications(skip = 0, limit = 20): Promise<NotificationListResponse> {
  return client
    .get<NotificationListResponse>('/api/v1/notifications', { params: { skip, limit } })
    .then((response) => response.data)
}

export function markNotificationRead(id: string): Promise<Notification> {
  return client
    .patch<Notification>(`/api/v1/notifications/${id}/read`)
    .then((response) => response.data)
}

export function markAllNotificationsRead(): Promise<{ updated: number }> {
  return client
    .post<{ updated: number }>('/api/v1/notifications/mark-all-read')
    .then((response) => response.data)
}
