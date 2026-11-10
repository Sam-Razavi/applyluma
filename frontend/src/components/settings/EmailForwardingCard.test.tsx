import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import EmailForwardingCard from './EmailForwardingCard'

const { mockGet, mockRotate } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockRotate: vi.fn(),
}))

vi.mock('../../services/emailForwardingApi', () => ({
  getEmailForwarding: mockGet,
  rotateEmailForwarding: mockRotate,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const enabled = {
  enabled: true,
  address: 'u-tok123@in.applyluma.com',
  emails_received: 0,
  last_received_at: null,
  gmail_confirmation: null,
}

function renderCard() {
  return render(
    <MemoryRouter>
      <EmailForwardingCard />
    </MemoryRouter>,
  )
}

describe('EmailForwardingCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing while the feature is off for this user', async () => {
    mockGet.mockResolvedValue({ ...enabled, enabled: false, address: null })
    const { container } = renderCard()

    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the address and that nothing has arrived yet', async () => {
    mockGet.mockResolvedValue(enabled)
    renderCard()

    expect(await screen.findByText('u-tok123@in.applyluma.com')).toBeInTheDocument()
    expect(screen.getByText('No emails received yet.')).toBeInTheDocument()
    expect(screen.getByText('Set up in Gmail')).toBeInTheDocument()
  })

  it("shows Gmail's confirmation code and link", async () => {
    mockGet.mockResolvedValue({
      ...enabled,
      emails_received: 1,
      gmail_confirmation: {
        code: '987654321',
        link: 'https://mail-settings.google.com/mail/vf-abc',
        received_at: '2026-11-10T10:00:00Z',
      },
    })
    renderCard()

    expect(await screen.findByText('987654321')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Confirm forwarding' })).toHaveAttribute(
      'href',
      'https://mail-settings.google.com/mail/vf-abc',
    )
  })

  it('replaces the address after confirmation', async () => {
    mockGet.mockResolvedValue(enabled)
    mockRotate.mockResolvedValue({ ...enabled, address: 'u-new456@in.applyluma.com' })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderCard()

    fireEvent.click(await screen.findByRole('button', { name: 'Get a new address' }))

    expect(await screen.findByText('u-new456@in.applyluma.com')).toBeInTheDocument()
    expect(mockRotate).toHaveBeenCalled()
  })

  it("hides Gmail's prompt after \"I've confirmed it\"", async () => {
    localStorage.clear()
    mockGet.mockResolvedValue({
      ...enabled,
      gmail_confirmation: { code: null, link: 'https://mail-settings.google.com/mail/vf-abc', received_at: '2026-11-10T10:00:00Z' },
    })
    renderCard()

    fireEvent.click(await screen.findByRole('button', { name: "I've confirmed it" }))

    expect(screen.queryByText('Gmail wants you to confirm forwarding')).not.toBeInTheDocument()
    expect(localStorage.getItem('applyluma_gmail_confirmation_dismissed')).toBe('2026-11-10T10:00:00Z')
  })

  it('tells Outlook users to redirect rather than forward', async () => {
    mockGet.mockResolvedValue(enabled)
    renderCard()

    expect(await screen.findByText('Set up in Outlook or Hotmail')).toBeInTheDocument()
    expect(screen.getByText('Redirect to')).toBeInTheDocument()
  })
})
