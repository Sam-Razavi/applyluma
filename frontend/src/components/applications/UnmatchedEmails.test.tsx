import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import UnmatchedEmails from './UnmatchedEmails'
import type { Application } from '../../types/application'

const { mockList, mockAssign, mockDismiss } = vi.hoisted(() => ({
  mockList: vi.fn(),
  mockAssign: vi.fn(),
  mockDismiss: vi.fn(),
}))

vi.mock('../../services/applicationsApi', () => ({
  listUnmatchedEmails: mockList,
  assignUnmatchedEmail: mockAssign,
  dismissUnmatchedEmail: mockDismiss,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const email = {
  id: 'em-1',
  from_address: 'noreply@teamtailor.com',
  subject: 'Your application',
  classification: 'rejection',
  suggested_status: 'rejected' as const,
  evidence: 'Unfortunately we have decided to move forward with other candidates.',
  received_at: null,
  created_at: '2026-11-10T10:00:00Z',
}

const applications = [
  { id: 'app-1', company_name: 'Klarna', job_title: 'Backend Engineer' },
  { id: 'app-2', company_name: 'Acme', job_title: 'Data Engineer' },
] as Application[]

describe('UnmatchedEmails', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the evidence and lists applications to choose from', async () => {
    mockList.mockResolvedValue({ items: [email] })
    render(<UnmatchedEmails applications={applications} onApplied={vi.fn()} />)

    expect(await screen.findByText('Which application is this email about?')).toBeInTheDocument()
    expect(screen.getByText(/move forward with other candidates/)).toBeInTheDocument()
    const options = screen.getAllByRole('option').map((o) => o.textContent)
    // Sorted by company, after the placeholder.
    expect(options).toEqual([
      'Choose the application…',
      'Acme — Data Engineer',
      'Klarna — Backend Engineer',
    ])
  })

  it('cannot apply until an application is chosen, then applies and refreshes', async () => {
    mockList.mockResolvedValue({ items: [email] })
    mockAssign.mockResolvedValue({ company_name: 'Klarna' })
    const onApplied = vi.fn()
    render(<UnmatchedEmails applications={applications} onApplied={onApplied} />)

    const apply = await screen.findByRole('button', { name: 'Update to Rejected' })
    expect(apply).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Application'), { target: { value: 'app-1' } })
    fireEvent.click(apply)

    await waitFor(() => expect(mockAssign).toHaveBeenCalledWith('em-1', 'app-1'))
    expect(onApplied).toHaveBeenCalled()
    await waitFor(() =>
      expect(screen.queryByText('Which application is this email about?')).not.toBeInTheDocument(),
    )
  })

  it('dismisses an email that is not about a job', async () => {
    mockList.mockResolvedValue({ items: [email] })
    mockDismiss.mockResolvedValue(undefined)
    render(<UnmatchedEmails applications={applications} onApplied={vi.fn()} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Not a job email' }))

    await waitFor(() => expect(mockDismiss).toHaveBeenCalledWith('em-1'))
  })

  it('renders nothing without unmatched emails', async () => {
    mockList.mockResolvedValue({ items: [] })
    const { container } = render(<UnmatchedEmails applications={applications} onApplied={vi.fn()} />)

    await waitFor(() => expect(mockList).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
