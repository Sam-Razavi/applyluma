import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdminStatusBanner from './AdminStatusBanner'

const { mockGetSystemHealth } = vi.hoisted(() => ({
  mockGetSystemHealth: vi.fn(),
}))

vi.mock('../../services/adminApi', () => ({
  adminApi: { getSystemHealth: mockGetSystemHealth },
}))

function renderBanner() {
  return render(
    <MemoryRouter>
      <AdminStatusBanner />
    </MemoryRouter>
  )
}

describe('AdminStatusBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing when the system is healthy', async () => {
    mockGetSystemHealth.mockResolvedValue({
      status: 'ok',
      version: '1.0.0',
      checks: { db: { status: 'ok', detail: 'ok' } },
    })
    renderBanner()

    await vi.waitFor(() => expect(mockGetSystemHealth).toHaveBeenCalled())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a red banner listing failing checks when unhealthy', async () => {
    mockGetSystemHealth.mockResolvedValue({
      status: 'unhealthy',
      version: '1.0.0',
      checks: {
        db: { status: 'unhealthy', detail: 'db down' },
        redis: { status: 'ok', detail: 'ok' },
      },
    })
    renderBanner()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('System unhealthy')
    expect(alert).toHaveTextContent('db')
    expect(screen.getByRole('link', { name: 'View details' })).toHaveAttribute(
      'href',
      '/admin/system',
    )
  })

  it('shows an amber banner when degraded', async () => {
    mockGetSystemHealth.mockResolvedValue({
      status: 'degraded',
      version: '1.0.0',
      checks: { redis: { status: 'degraded', detail: 'redis slow' } },
    })
    renderBanner()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('System degraded')
    expect(alert.className).toContain('bg-amber-600')
  })

  it('polls again after the interval and clears the banner on recovery', async () => {
    mockGetSystemHealth
      .mockResolvedValueOnce({
        status: 'degraded',
        version: '1.0.0',
        checks: { redis: { status: 'degraded', detail: 'redis slow' } },
      })
      .mockResolvedValueOnce({
        status: 'ok',
        version: '1.0.0',
        checks: { redis: { status: 'ok', detail: 'ok' } },
      })
    renderBanner()

    await screen.findByRole('alert')

    await vi.advanceTimersByTimeAsync(60_000)
    await waitFor(() => expect(mockGetSystemHealth).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })
})
