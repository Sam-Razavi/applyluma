import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Settings from './Settings'
import { authApi } from '../services/authApi'
import { useAuthStore } from '../stores'
import type { User } from '../types'

vi.mock('../services/api', () => ({
  cvApi: { list: vi.fn().mockResolvedValue([]) },
}))

vi.mock('../services/alertsApi', () => ({
  getPreferences: vi.fn().mockResolvedValue({
    id: 'p-1',
    user_id: 'u-1',
    enabled: false,
    score_threshold: 70,
    frequency: 'daily',
    last_sent_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }),
  updatePreferences: vi.fn(),
}))

vi.mock('../services/authApi', () => ({
  authApi: {
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    deleteAccount: vi.fn(),
    logout: vi.fn(),
  },
}))

vi.mock('../services/tailorApi', () => ({
  tailorApi: {
    getUsage: vi.fn().mockResolvedValue({
      used_today: 0,
      daily_limit: 1,
      resets_at: '2026-01-02T00:00:00Z',
    }),
  },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u-1',
    email: 'sam@example.com',
    full_name: 'Sam',
    is_active: true,
    is_verified: true,
    role: 'user',
    preferred_template: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderSettings(user: User) {
  useAuthStore.setState({ user, isAuthenticated: true })
  return render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>,
  )
}

describe('Settings — default CV template', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('renders the template dropdown with the stored preference selected', async () => {
    renderSettings(makeUser({ preferred_template: 'executive' }))

    const select = await screen.findByLabelText<HTMLSelectElement>(/default cv template/i)
    expect(select.value).toBe('executive')
    expect(screen.getByRole('option', { name: 'Nordic' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Modern' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Compact' })).toBeInTheDocument()
  })

  it('defaults to nordic when no preference is stored', async () => {
    renderSettings(makeUser())

    const select = await screen.findByLabelText<HTMLSelectElement>(/default cv template/i)
    expect(select.value).toBe('nordic')
  })

  it('saves the chosen template through authApi.updateProfile', async () => {
    const user = makeUser()
    vi.mocked(authApi.updateProfile).mockResolvedValue({
      ...user,
      preferred_template: 'modern',
    })
    renderSettings(user)

    const select = await screen.findByLabelText<HTMLSelectElement>(/default cv template/i)
    fireEvent.change(select, { target: { value: 'modern' } })
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }))

    await waitFor(() =>
      expect(authApi.updateProfile).toHaveBeenCalledWith({
        full_name: 'Sam',
        preferred_template: 'modern',
      }),
    )
    expect(useAuthStore.getState().user?.preferred_template).toBe('modern')
  })
})
