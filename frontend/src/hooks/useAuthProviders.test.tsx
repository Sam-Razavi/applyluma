import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { FALLBACK_PROVIDERS, useAuthProviders } from './useAuthProviders'
import { authApi } from '../services/authApi'

vi.mock('../services/authApi', () => ({
  authApi: {
    getProviders: vi.fn(),
  },
}))

describe('useAuthProviders', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the backend-reported providers once loaded', async () => {
    const fromBackend = { google: true, linkedin: true, github: false, magic_link: true }
    vi.mocked(authApi.getProviders).mockResolvedValueOnce(fromBackend)

    const { result } = renderHook(() => useAuthProviders())

    await waitFor(() => expect(result.current).toEqual(fromBackend))
  })

  it('keeps the Google-only fallback when the fetch fails', async () => {
    vi.mocked(authApi.getProviders).mockRejectedValueOnce(new Error('network'))

    const { result } = renderHook(() => useAuthProviders())

    await waitFor(() => expect(authApi.getProviders).toHaveBeenCalled())
    expect(result.current).toEqual(FALLBACK_PROVIDERS)
  })
})
