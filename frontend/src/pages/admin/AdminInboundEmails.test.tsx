import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AdminInboundEmails from './AdminInboundEmails'

const { mockListInboundEmails } = vi.hoisted(() => ({
  mockListInboundEmails: vi.fn(),
}))

vi.mock('../../services/adminApi', () => ({
  adminApi: { listInboundEmails: mockListInboundEmails },
}))

const matchedRow = {
  id: 'row-1',
  user_id: 'user-1',
  from_address: 'careers@spotify.com',
  from_domain: 'spotify.com',
  subject: 'Your application to Spotify',
  snippet: 'Thanks for applying to the Backend Engineer role.',
  message_id: '<m1@spotify.com>',
  received_at: '2026-08-26T10:00:00Z',
  vendor: 'generic',
  matched_application_id: 'app-1',
  matched_company_name: 'Spotify AB',
  matched_job_title: 'Backend Engineer',
  match_confidence: 90,
  match_method: 'job_url_domain',
  match_reason: 'Sender domain spotify.com matches the job URL host jobs.spotify.com.',
  created_at: '2026-08-26T10:01:00Z',
}

const unmatchedRow = {
  ...matchedRow,
  id: 'row-2',
  from_address: 'no-reply@greenhouse.io',
  from_domain: 'greenhouse.io',
  subject: 'An update on your application',
  matched_application_id: null,
  matched_company_name: null,
  matched_job_title: null,
  match_confidence: 55,
  match_method: 'ats_body',
  match_reason: 'Company found in the body only. Below the 70 confidence threshold.',
}

function response(items: unknown[]) {
  return { items, total: items.length, page: 1, size: 25 }
}

describe('AdminInboundEmails', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders a matched row with the application it matched to', async () => {
    mockListInboundEmails.mockResolvedValue(response([matchedRow]))
    render(<AdminInboundEmails />)

    expect(await screen.findByText('Spotify AB')).toBeInTheDocument()
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('90')).toBeInTheDocument()
    expect(screen.getByText('job_url_domain')).toBeInTheDocument()
  })

  it('shows the match reason so a decision can be diagnosed', async () => {
    mockListInboundEmails.mockResolvedValue(response([matchedRow]))
    render(<AdminInboundEmails />)

    expect(await screen.findByText(/matches the job URL host/)).toBeInTheDocument()
  })

  it('marks an unmatched row rather than inventing a link', async () => {
    mockListInboundEmails.mockResolvedValue(response([unmatchedRow]))
    render(<AdminInboundEmails />)

    expect(await screen.findByText('Unmatched')).toBeInTheDocument()
    expect(screen.getByText('ats_body')).toBeInTheDocument()
  })

  it('refetches with the matched filter when a chip is clicked', async () => {
    mockListInboundEmails.mockResolvedValue(response([matchedRow]))
    render(<AdminInboundEmails />)
    await screen.findByText('Spotify AB')

    fireEvent.click(screen.getByRole('button', { name: 'Unmatched' }))

    await waitFor(() =>
      expect(mockListInboundEmails).toHaveBeenLastCalledWith(
        expect.objectContaining({ matched: false }),
      ),
    )
  })

  it('reveals the snippet when a row is expanded', async () => {
    mockListInboundEmails.mockResolvedValue(response([matchedRow]))
    render(<AdminInboundEmails />)
    const subject = await screen.findByText('Your application to Spotify')

    expect(screen.queryByText(/Thanks for applying/)).not.toBeInTheDocument()
    fireEvent.click(subject)
    expect(await screen.findByText(/Thanks for applying/)).toBeInTheDocument()
  })

  it('shows an empty state when nothing has arrived', async () => {
    mockListInboundEmails.mockResolvedValue(response([]))
    render(<AdminInboundEmails />)

    expect(await screen.findByText('No inbound mail yet')).toBeInTheDocument()
  })

  it('shows an error banner when the request fails', async () => {
    mockListInboundEmails.mockRejectedValue(new Error('boom'))
    render(<AdminInboundEmails />)

    expect(await screen.findByText('Failed to load inbound emails')).toBeInTheDocument()
  })
})
