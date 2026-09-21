import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import EmailSuggestions from './EmailSuggestions'

const { mockList, mockAccept, mockDismiss } = vi.hoisted(() => ({
  mockList: vi.fn(),
  mockAccept: vi.fn(),
  mockDismiss: vi.fn(),
}))

vi.mock('../../services/applicationsApi', () => ({
  listEmailSuggestions: mockList,
  acceptEmailSuggestion: mockAccept,
  dismissEmailSuggestion: mockDismiss,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const suggestion = {
  id: 'sug-1',
  application_id: 'app-1',
  company_name: 'Svea Solar',
  job_title: 'Backend Engineer',
  current_status: 'applied' as const,
  suggested_status: 'rejected' as const,
  classification: 'rejection',
  confidence: 90,
  evidence: 'Tyvärr har du inte gått vidare i processen.',
  from_address: 'hr@sveasolar.com',
  subject: 'Din ansökan',
  received_at: null,
}

describe('EmailSuggestions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the proposed change and the sentence behind it', async () => {
    mockList.mockResolvedValue({ items: [suggestion] })
    render(<EmailSuggestions onApplied={vi.fn()} />)

    expect(await screen.findByText('Svea Solar')).toBeInTheDocument()
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByText('Rejected')).toBeInTheDocument()
    expect(screen.getByText(/inte gått vidare/)).toBeInTheDocument()
  })

  it('renders nothing when there are no suggestions', async () => {
    mockList.mockResolvedValue({ items: [] })
    const { container } = render(<EmailSuggestions onApplied={vi.fn()} />)

    await waitFor(() => expect(mockList).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('applies the change and refreshes the board on accept', async () => {
    mockList.mockResolvedValue({ items: [suggestion] })
    mockAccept.mockResolvedValue({})
    const onApplied = vi.fn()
    render(<EmailSuggestions onApplied={onApplied} />)
    await screen.findByText('Svea Solar')

    fireEvent.click(screen.getByRole('button', { name: /Update to Rejected/ }))

    await waitFor(() => expect(mockAccept).toHaveBeenCalledWith('sug-1'))
    await waitFor(() => expect(onApplied).toHaveBeenCalled())
    expect(screen.queryByText('Svea Solar')).not.toBeInTheDocument()
  })

  it('dismisses without touching the application', async () => {
    mockList.mockResolvedValue({ items: [suggestion] })
    mockDismiss.mockResolvedValue(undefined)
    const onApplied = vi.fn()
    render(<EmailSuggestions onApplied={onApplied} />)
    await screen.findByText('Svea Solar')

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))

    await waitFor(() => expect(mockDismiss).toHaveBeenCalledWith('sug-1'))
    expect(mockAccept).not.toHaveBeenCalled()
    expect(onApplied).not.toHaveBeenCalled()
  })

  it('stays silent when the request fails', async () => {
    mockList.mockRejectedValue(new Error('boom'))
    const { container } = render(<EmailSuggestions onApplied={vi.fn()} />)

    await waitFor(() => expect(mockList).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
