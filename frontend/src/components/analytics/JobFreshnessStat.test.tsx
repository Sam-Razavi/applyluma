import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import JobFreshnessStat from './JobFreshnessStat'
import { analyticsApi } from '../../services/api'

vi.mock('../../services/api', () => ({
  analyticsApi: { freshness: vi.fn() },
}))

const mockFreshness = vi.mocked(analyticsApi.freshness)

describe('JobFreshnessStat', () => {
  beforeEach(() => {
    mockFreshness.mockReset()
  })

  it('shows new jobs today when there are fresh jobs', async () => {
    mockFreshness.mockResolvedValue({
      total_jobs: 812,
      new_today: 37,
      new_this_week: 190,
      last_updated: new Date().toISOString(),
    })

    render(<JobFreshnessStat />)

    await waitFor(() => expect(screen.getByText('37 new jobs today')).toBeInTheDocument())
    expect(screen.getByText(/812 total/)).toBeInTheDocument()
  })

  it('falls back to total count when nothing new today', async () => {
    mockFreshness.mockResolvedValue({
      total_jobs: 500,
      new_today: 0,
      new_this_week: 12,
      last_updated: new Date().toISOString(),
    })

    render(<JobFreshnessStat />)

    await waitFor(() => expect(screen.getByText('500 jobs tracked')).toBeInTheDocument())
  })

  it('renders nothing when the request fails', async () => {
    mockFreshness.mockRejectedValue(new Error('boom'))

    const { container } = render(<JobFreshnessStat />)

    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })
})
