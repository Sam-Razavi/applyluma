import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AxiosError, AxiosHeaders } from 'axios'
import ExtensionAuth from './ExtensionAuth'
import { useAuthStore } from '../stores'

const { mockRefresh, mockExtensionToken } = vi.hoisted(() => ({
  mockRefresh: vi.fn(),
  mockExtensionToken: vi.fn(),
}))

vi.mock('../services/api', () => ({
  authApi: { refresh: mockRefresh, extensionToken: mockExtensionToken },
}))

function unauthorized() {
  return new AxiosError('401', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 401,
    statusText: 'Unauthorized',
    data: {},
    headers: {},
    config: { headers: new AxiosHeaders() },
  })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ExtensionAuth />
    </MemoryRouter>,
  )
}

describe('ExtensionAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  })

  it('in a fresh tab, trades the refresh cookie for a token before minting', async () => {
    mockRefresh.mockResolvedValue({ access_token: 'fresh-access' })
    mockExtensionToken.mockResolvedValue({
      access_token: 'ext-access',
      refresh_token: 'ext-refresh',
      token_type: 'bearer',
    })
    renderPage()

    expect(await screen.findByText(/Token copied/)).toBeInTheDocument()
    expect(mockRefresh).toHaveBeenCalled()
    expect(useAuthStore.getState().token).toBe('fresh-access')
    expect(screen.getByRole('button', { name: /Copy token/ })).toBeEnabled()
  })

  it('skips the refresh when this tab already has a token', async () => {
    useAuthStore.getState().setToken('existing')
    mockExtensionToken.mockResolvedValue({
      access_token: 'ext-access',
      refresh_token: 'ext-refresh',
      token_type: 'bearer',
    })
    renderPage()

    expect(await screen.findByText(/Token copied/)).toBeInTheDocument()
    expect(mockRefresh).not.toHaveBeenCalled()
  })

  it('offers sign-in that returns here when the browser is signed out', async () => {
    mockRefresh.mockRejectedValue(unauthorized())
    renderPage()

    const link = await screen.findByRole('link', { name: 'Sign in' })
    expect(link).toHaveAttribute('href', '/login?next=/extension-auth')
    expect(mockExtensionToken).not.toHaveBeenCalled()
  })

  it('shows the generic error for anything else', async () => {
    mockRefresh.mockRejectedValue(new Error('network down'))
    renderPage()

    expect(await screen.findByText(/Could not generate a token/)).toBeInTheDocument()
  })
})
