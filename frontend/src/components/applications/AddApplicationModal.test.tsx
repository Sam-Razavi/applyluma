import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AddApplicationModal from './AddApplicationModal'
import { jobApi } from '../../services/api'

vi.mock('../../services/api', () => ({
  jobApi: { scrapeUrl: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const scrapeResult = {
  company_name: 'Acme AB',
  job_title: 'Systemutvecklare',
  description: 'Vi söker en systemutvecklare.',
  url: 'https://arbetsformedlingen.se/platsbanken/annonser/29403394',
  location: 'Stockholm',
}

function renderModal() {
  return render(<AddApplicationModal open onClose={vi.fn()} />)
}

describe('AddApplicationModal — import from URL', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the import section', () => {
    renderModal()
    expect(screen.getByLabelText('Import from URL')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Extract' })).toBeInTheDocument()
  })

  it('pre-fills the form from a scraped URL', async () => {
    vi.mocked(jobApi.scrapeUrl).mockResolvedValue(scrapeResult)
    renderModal()

    fireEvent.change(screen.getByLabelText('Import from URL'), {
      target: { value: 'https://arbetsformedlingen.se/platsbanken/annonser/29403394' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Extract' }))

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Spotify')).toHaveValue('Acme AB')
    })
    expect(jobApi.scrapeUrl).toHaveBeenCalledWith(
      'https://arbetsformedlingen.se/platsbanken/annonser/29403394',
    )
    expect(screen.getByPlaceholderText('Backend Engineer')).toHaveValue('Systemutvecklare')
    expect(screen.getByPlaceholderText('https://...')).toHaveValue(scrapeResult.url)
    expect(screen.getByPlaceholderText('Stockholm')).toHaveValue('Stockholm')
    expect(screen.getByLabelText('Source')).toHaveValue('other')
  })

  it('derives linkedin source from the URL hostname', async () => {
    vi.mocked(jobApi.scrapeUrl).mockResolvedValue({
      ...scrapeResult,
      url: 'https://www.linkedin.com/jobs/view/123',
      location: null,
    })
    renderModal()

    fireEvent.change(screen.getByLabelText('Import from URL'), {
      target: { value: 'https://www.linkedin.com/jobs/view/123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Extract' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Source')).toHaveValue('linkedin')
    })
  })

  it('shows the backend error detail inline on failure', async () => {
    vi.mocked(jobApi.scrapeUrl).mockRejectedValue({
      response: { data: { detail: 'This page requires a login to view job details.' } },
    })
    renderModal()

    fireEvent.change(screen.getByLabelText('Import from URL'), {
      target: { value: 'https://www.linkedin.com/jobs/view/123' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Extract' }))

    await waitFor(() => {
      expect(
        screen.getByText('This page requires a login to view job details.'),
      ).toBeInTheDocument()
    })
  })

  it('shows a generic error when no detail is present', async () => {
    vi.mocked(jobApi.scrapeUrl).mockRejectedValue(new Error('network'))
    renderModal()

    fireEvent.change(screen.getByLabelText('Import from URL'), {
      target: { value: 'https://example.com/job' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Extract' }))

    await waitFor(() => {
      expect(
        screen.getByText('Could not extract job details from that URL'),
      ).toBeInTheDocument()
    })
  })
})
