import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreateFromEmail from './CreateFromEmail'
import * as api from '../../services/emailForwardingApi'
import type { ForwardedEmail } from '../../services/emailForwardingApi'

vi.mock('../../services/emailForwardingApi')
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

const email: ForwardedEmail = {
  id: 'e1',
  from_address: 'jobs@spotify.com',
  subject: 'Your application for Backend Engineer at Spotify',
  snippet: 'Thanks for applying.',
  received_at: '2026-11-14T10:00:00Z',
  created_at: '2026-11-14T10:00:05Z',
  classification: 'acknowledged',
  suggested_status: null,
  evidence: null,
  suggestion_state: 'none',
  application_id: null,
  company_name: null,
  job_title: null,
  guessed_company: 'Spotify',
  guessed_title: 'Backend Engineer',
}

describe('CreateFromEmail', () => {
  beforeEach(() => vi.clearAllMocks())

  it('prefills the guess and creates the application with the edited values', async () => {
    vi.mocked(api.createApplicationFromEmail).mockResolvedValue({
      id: 'a1', company_name: 'Spotify AB', job_title: 'Backend Engineer', status: 'applied',
    })
    const onCreated = vi.fn()
    render(<CreateFromEmail email={email} onCreated={onCreated} />)

    await userEvent.click(screen.getByRole('button', { name: /create application from this email/i }))
    const company = screen.getByLabelText('Company')
    expect(company).toHaveValue('Spotify')
    expect(screen.getByLabelText('Job title')).toHaveValue('Backend Engineer')

    await userEvent.clear(company)
    await userEvent.type(company, 'Spotify AB')
    await userEvent.click(screen.getByRole('button', { name: 'Create application' }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ id: 'a1' })))
    expect(api.createApplicationFromEmail).toHaveBeenCalledWith('e1', {
      company_name: 'Spotify AB',
      job_title: 'Backend Engineer',
    })
  })

  it('cannot be submitted until both fields are filled', async () => {
    render(<CreateFromEmail email={{ ...email, guessed_company: null, guessed_title: null }} onCreated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /create application from this email/i }))
    expect(screen.getByRole('button', { name: 'Create application' })).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Company'), 'Acme')
    expect(screen.getByRole('button', { name: 'Create application' })).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Job title'), 'Developer')
    expect(screen.getByRole('button', { name: 'Create application' })).toBeEnabled()
  })
})
