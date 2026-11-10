import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import NotificationBell from './NotificationBell'
import { useNotificationsStore } from '../../stores/notifications'

const { mockMarkRead } = vi.hoisted(() => ({ mockMarkRead: vi.fn() }))

vi.mock('../../services/notificationsApi', () => ({
  fetchNotifications: vi.fn(),
  markNotificationRead: mockMarkRead,
  markAllNotificationsRead: vi.fn(),
}))

function notification(overrides: Record<string, unknown> = {}) {
  return {
    id: 'n1',
    user_id: 'u1',
    type: 'email_status_suggestion',
    title: 'Possible rejection',
    body: 'An email from talent@supportwave.com looks like a rejection.',
    related_id: null,
    related_type: null,
    is_read: false,
    created_at: '2026-11-10T20:00:00Z',
    updated_at: '2026-11-10T20:00:00Z',
    ...overrides,
  }
}

function renderBell() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/dashboard" element={<NotificationBell />} />
        <Route path="/applications" element={<p>applications page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockMarkRead.mockResolvedValue(undefined)
  })

  it('shows the unread count and the notifications when opened', () => {
    useNotificationsStore.setState({
      notifications: [notification(), notification({ id: 'n2', type: 'admin_message', title: 'Hello from admin', is_read: true })],
      unreadCount: 1,
      isLoading: false,
    })
    renderBell()

    expect(screen.getByRole('button', { name: 'Notifications, 1 unread' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Notifications/ }))

    expect(screen.getByText('Possible rejection')).toBeInTheDocument()
    expect(screen.getByText('Hello from admin')).toBeInTheDocument()
  })

  it('opens the page a notification is about and marks it read', async () => {
    useNotificationsStore.setState({ notifications: [notification()], unreadCount: 1, isLoading: false })
    renderBell()

    fireEvent.click(screen.getByRole('button', { name: /Notifications/ }))
    fireEvent.click(screen.getByText('Possible rejection'))

    expect(await screen.findByText('applications page')).toBeInTheDocument()
    expect(mockMarkRead).toHaveBeenCalledWith('n1')
  })
})
