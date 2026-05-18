import { create } from 'zustand'
import {
  fetchNotifications as fetchNotificationsApi,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from '../services/notificationsApi'

interface NotificationsState {
  notifications: Notification[]
  unreadCount: number
  isLoading: boolean
  error: string | null
  fetchNotifications: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
}

export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetchNotificationsApi()
      set({
        notifications: response.items,
        unreadCount: response.unread_count,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load notifications',
        isLoading: false,
      })
    }
  },

  markRead: async (id: string) => {
    const before = get().notifications
    set((state) => ({
      notifications: state.notifications.map((notification) =>
        notification.id === id ? { ...notification, is_read: true } : notification,
      ),
      unreadCount: Math.max(0, state.unreadCount - (state.notifications.find((n) => n.id === id)?.is_read ? 0 : 1)),
    }))
    try {
      const updated = await markNotificationRead(id)
      set((state) => ({
        notifications: state.notifications.map((notification) =>
          notification.id === id ? updated : notification,
        ),
      }))
    } catch (error) {
      set({
        notifications: before,
        unreadCount: before.filter((notification) => !notification.is_read).length,
        error: error instanceof Error ? error.message : 'Failed to mark notification read',
      })
    }
  },

  markAllRead: async () => {
    const before = get().notifications
    set((state) => ({
      notifications: state.notifications.map((notification) => ({ ...notification, is_read: true })),
      unreadCount: 0,
    }))
    try {
      await markAllNotificationsRead()
    } catch (error) {
      set({
        notifications: before,
        unreadCount: before.filter((notification) => !notification.is_read).length,
        error: error instanceof Error ? error.message : 'Failed to mark notifications read',
      })
    }
  },
}))
