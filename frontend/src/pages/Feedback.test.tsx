import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Feedback from './Feedback'
import toast from 'react-hot-toast'

const { mockSubmit } = vi.hoisted(() => ({ mockSubmit: vi.fn() }))

vi.mock('../services/api', () => ({
  feedbackApi: { submit: mockSubmit },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

describe('Feedback', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the form with category options', () => {
    render(<Feedback />)
    expect(screen.getByRole('heading', { name: 'Send feedback' })).toBeInTheDocument()
    expect(screen.getByLabelText('Category')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Bug report' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Feature request' })).toBeInTheDocument()
  })

  it('rejects a message shorter than 10 characters without calling the API', () => {
    render(<Feedback />)
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'short' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send feedback' }))
    expect(mockSubmit).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalled()
  })

  it('submits category, subject, and message, then clears the form', async () => {
    mockSubmit.mockResolvedValue({ ok: true })
    render(<Feedback />)

    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'feature' } })
    fireEvent.change(screen.getByLabelText(/Subject/), { target: { value: 'Dark mode charts' } })
    fireEvent.change(screen.getByLabelText('Message'), {
      target: { value: 'Please add dark-mode friendly analytics charts.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send feedback' }))

    await waitFor(() =>
      expect(mockSubmit).toHaveBeenCalledWith({
        category: 'feature',
        subject: 'Dark mode charts',
        message: 'Please add dark-mode friendly analytics charts.',
      }),
    )
    expect(toast.success).toHaveBeenCalled()
    expect(screen.getByLabelText('Message')).toHaveValue('')
  })

  it('shows an error toast when the API fails', async () => {
    mockSubmit.mockRejectedValue(new Error('boom'))
    render(<Feedback />)
    fireEvent.change(screen.getByLabelText('Message'), {
      target: { value: 'This is a valid feedback message.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send feedback' }))
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
