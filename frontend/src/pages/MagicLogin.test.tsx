import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import MagicLogin from './MagicLogin'
import { authApi } from '../services/api'
import { authApi as authExtraApi } from '../services/authApi'
import { useAuthStore } from '../stores'

vi.mock('../services/api', () => ({
  authApi: {
    me: vi.fn(),
  },
}))

vi.mock('../services/authApi', () => ({
  authApi: {
    verifyMagicLink: vi.fn(),
  },
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const TOKEN_PAIR = { access_token: 'magic-access', refresh_token: 'magic-refresh' }
const USER = { id: '1', email: 'sam@example.com', full_name: 'Sam' }

function renderPage(path = '/magic-login?token=tok-1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <MagicLogin />
    </MemoryRouter>,
  )
}

describe('MagicLogin page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('verifies the token, stores the session, and navigates to the dashboard', async () => {
    vi.mocked(authExtraApi.verifyMagicLink).mockResolvedValueOnce(TOKEN_PAIR)
    vi.mocked(authApi.me).mockResolvedValueOnce(USER as never)

    renderPage()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
    expect(authExtraApi.verifyMagicLink).toHaveBeenCalledWith('tok-1')
    const state = useAuthStore.getState()
    expect(state.token).toBe('magic-access')
    expect(state.refreshToken).toBe('magic-refresh')
    expect(state.user).toEqual(USER)
  })

  it('redirects to login with an error when the token is missing', async () => {
    renderPage('/magic-login')

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?error=magic_link_failed', { replace: true })
    })
    expect(authExtraApi.verifyMagicLink).not.toHaveBeenCalled()
  })

  it('redirects to login with an error when verification fails', async () => {
    vi.mocked(authExtraApi.verifyMagicLink).mockRejectedValueOnce(new Error('expired'))

    renderPage()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?error=magic_link_failed', { replace: true })
    })
    expect(authApi.me).not.toHaveBeenCalled()
  })
})
