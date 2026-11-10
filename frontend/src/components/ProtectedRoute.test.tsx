import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import { useAuthStore } from '../stores'
import { resetRestoreForTests } from '../lib/session'

const { mockRefresh, mockMe } = vi.hoisted(() => ({ mockRefresh: vi.fn(), mockMe: vi.fn() }))

vi.mock('../services/api', () => ({ authApi: { refresh: mockRefresh, me: mockMe } }))
vi.mock('posthog-js', () => ({ default: { identify: vi.fn(), reset: vi.fn() } }))

function LoginProbe() {
  const location = useLocation()
  return <p>login page {location.search}</p>
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/discover" element={<p>saved jobs</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute in a new tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
    resetRestoreForTests()
  })

  it('restores the session from the cookie instead of asking to sign in again', async () => {
    mockRefresh.mockResolvedValue({ access_token: 'fresh' })
    mockMe.mockResolvedValue({ id: 'u1', email: 'sam@example.com', role: 'user' })

    renderAt('/discover?tab=saved')

    expect(await screen.findByText('saved jobs')).toBeInTheDocument()
  })

  it('sends a signed-out visitor to login and back to the page they wanted', async () => {
    mockRefresh.mockRejectedValue(new Error('401'))

    renderAt('/discover?tab=saved')

    const login = await screen.findByText(/login page/)
    expect(login.textContent).toContain('next=%2Fdiscover%3Ftab%3Dsaved')
  })
})
