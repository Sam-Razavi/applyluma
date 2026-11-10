import { describe, it, expect, vi, beforeEach } from 'vitest'
import { hasSignedInHint, resetRestoreForTests, restoreSession } from './session'
import { useAuthStore } from '../stores'

const { mockRefresh, mockMe } = vi.hoisted(() => ({ mockRefresh: vi.fn(), mockMe: vi.fn() }))

vi.mock('../services/api', () => ({ authApi: { refresh: mockRefresh, me: mockMe } }))
vi.mock('posthog-js', () => ({ default: { identify: vi.fn(), reset: vi.fn() } }))

const user = { id: 'u1', email: 'sam@example.com', role: 'user' }

describe('restoreSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
    localStorage.clear()
    resetRestoreForTests()
  })

  it('signs in from the refresh cookie and remembers this browser signed in', async () => {
    mockRefresh.mockResolvedValue({ access_token: 'fresh' })
    mockMe.mockResolvedValue(user)

    await expect(restoreSession()).resolves.toBe(true)

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.token).toBe('fresh')
    expect(hasSignedInHint()).toBe(true)
  })

  it('stays signed out, and forgets the hint, when the cookie is no longer valid', async () => {
    localStorage.setItem('applyluma_signed_in', '1')
    mockRefresh.mockRejectedValue(new Error('401'))

    await expect(restoreSession()).resolves.toBe(false)

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(hasSignedInHint()).toBe(false)
  })

  it('shares one attempt between concurrent callers', async () => {
    mockRefresh.mockResolvedValue({ access_token: 'fresh' })
    mockMe.mockResolvedValue(user)

    const [a, b] = await Promise.all([restoreSession(), restoreSession()])

    expect(a && b).toBe(true)
    expect(mockRefresh).toHaveBeenCalledTimes(1)
  })

  it('tries only once per page load, so signing out sticks', async () => {
    mockRefresh.mockResolvedValue({ access_token: 'fresh' })
    mockMe.mockResolvedValue(user)
    await restoreSession()
    useAuthStore.getState().logout() // the user signs out in this tab

    await expect(restoreSession()).resolves.toBe(false)
    expect(mockRefresh).toHaveBeenCalledTimes(1)
  })
})
