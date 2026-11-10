import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import EmailInbox from './EmailInbox'

const { mockList, mockDelete } = vi.hoisted(() => ({
  mockList: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('../../services/emailForwardingApi', () => ({
  listForwardedEmails: mockList,
  deleteForwardedEmail: mockDelete,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const matched = {
  id: 'em-1',
  from_address: 'talent@supportwave.com',
  subject: 'Application Unsuccessful',
  snippet: 'We regret to inform you that your application has been unsuccessful.',
  received_at: '2026-11-10T20:18:57Z',
  created_at: '2026-11-10T20:18:57Z',
  classification: 'rejection' as const,
  suggested_status: 'rejected',
  evidence: 'We regret to inform you',
  suggestion_state: 'pending' as const,
  application_id: 'app-1',
  company_name: 'supportwave',
  job_title: 'IT Support Specialist',
}

const unmatched = {
  ...matched,
  id: 'em-2',
  from_address: 'newsletter@jobs.example',
  subject: 'New jobs for you',
  classification: null,
  suggested_status: null,
  evidence: null,
  suggestion_state: 'none' as const,
  application_id: null,
  company_name: null,
  job_title: null,
}

function renderInbox() {
  return render(
    <MemoryRouter>
      <EmailInbox />
    </MemoryRouter>,
  )
}

describe('EmailInbox', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows what each email was detected as and what it matched', async () => {
    mockList.mockResolvedValue({ items: [matched, unmatched], total: 2 })
    renderInbox()

    expect(await screen.findByText('talent@supportwave.com')).toBeInTheDocument()
    expect(screen.getByText('Rejection')).toBeInTheDocument()
    expect(screen.getByText('supportwave — IT Support Specialist')).toBeInTheDocument()
    expect(screen.getByText(/Waiting for your decision/)).toBeInTheDocument()
    expect(screen.getByText('Nothing detected')).toBeInTheDocument()
    // Once as the filter button, once as the unmatched email's badge.
    expect(screen.getAllByText('Not matched')).toHaveLength(2)
  })

  it('expands to show the kept text', async () => {
    mockList.mockResolvedValue({ items: [matched], total: 1 })
    renderInbox()

    fireEvent.click(await screen.findByText('talent@supportwave.com'))

    expect(screen.getByText(/has been unsuccessful/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Delete/ })).toBeInTheDocument()
  })

  it('filters by matched / not matched', async () => {
    mockList.mockResolvedValue({ items: [], total: 0 })
    renderInbox()
    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: 'Not matched' }))

    await waitFor(() =>
      expect(mockList).toHaveBeenLastCalledWith({ skip: 0, limit: 20, matched: false }),
    )
  })

  it('deletes after confirmation', async () => {
    mockList.mockResolvedValue({ items: [matched], total: 1 })
    mockDelete.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderInbox()

    fireEvent.click(await screen.findByText('talent@supportwave.com'))
    fireEvent.click(screen.getByRole('button', { name: /Delete/ }))

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('em-1'))
    await waitFor(() => expect(screen.queryByText('talent@supportwave.com')).not.toBeInTheDocument())
  })

  it('loads more when there are more emails', async () => {
    mockList
      .mockResolvedValueOnce({ items: [matched], total: 2 })
      .mockResolvedValueOnce({ items: [unmatched], total: 2 })
    renderInbox()

    fireEvent.click(await screen.findByRole('button', { name: /Load more/ }))

    expect(await screen.findByText('newsletter@jobs.example')).toBeInTheDocument()
    expect(mockList).toHaveBeenLastCalledWith({ skip: 1, limit: 20, matched: undefined })
  })
})
