import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuthStore } from '../../stores'

vi.mock('../../services/authApi', () => ({ authApi: { logout: vi.fn() } }))
vi.mock('../../services/adminApi', () => ({ adminApi: { getContactStats: vi.fn() } }))
vi.mock('../notifications/NotificationBell', () => ({
  default: () => <button type="button" aria-label="Notifications" />,
}))

describe('Sidebar', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    useAuthStore.setState({
      user: { id: 'u1', email: 'sam@example.com', full_name: 'Sam', role: 'user' } as never,
    })
  })

  it('keeps one button next to the logo, so the bell stays inside the 224 px sidebar', () => {
    const { container } = render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    )
    // The header row holds the logo link and the bell; the theme switch
    // pushed the bell past the edge when it sat here too.
    const header = container.querySelector('aside > div') as HTMLElement
    expect(within(header).getAllByRole('button').map((b) => b.getAttribute('aria-label'))).toEqual([
      'Notifications',
    ])
    expect(screen.getByRole('button', { name: /switch to (dark|light) mode/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument()
  })
})
