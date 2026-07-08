import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AddApplicationModal from './AddApplicationModal'
import { jobApi } from '../../services/api'

const { mockCheckDuplicate, mockCreateApplication } = vi.hoisted(() => ({
  mockCheckDuplicate: vi.fn(),
  mockCreateApplication: vi.fn(),
}))

vi.mock('../../services/api', () => ({
  jobApi: { scrapeUrl: vi.fn() },
}))

vi.mock('../../services/applicationsApi', () => ({
  checkDuplicateApplication: mockCheckDuplicate,
}))

vi.mock('../../stores/applications', () => ({
  useApplicationsStore: (
    selector: (state: { createApplication: typeof mockCreateApplication }) => unknown,
  ) => selector({ createApplication: mockCreateApplication }),
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

describe('AddApplicationModal — duplicate warning', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function fillRequiredFields() {
    fireEvent.change(screen.getByPlaceholderText('Spotify'), { target: { value: 'Acme' } })
    fireEvent.change(screen.getByPlaceholderText('Backend Engineer'), {
      target: { value: 'Developer' },
    })
  }

  const openDuplicate = {
    duplicate: true,
    application: {
      id: '1',
      company_name: 'Acme',
      job_title: 'Old role',
      status: 'applied',
      created_at: '2026-01-01T00:00:00Z',
    },
  }

  it('warns instead of creating when an open application for the company exists', async () => {
    mockCheckDuplicate.mockResolvedValue(openDuplicate)
    renderModal()
    fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Save application' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Old role')
    expect(mockCreateApplication).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Add anyway' })).toBeInTheDocument()
  })

  it('creates on second submit after the warning is shown', async () => {
    mockCheckDuplicate.mockResolvedValue(openDuplicate)
    mockCreateApplication.mockResolvedValue(undefined)
    renderModal()
    fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Save application' }))
    await screen.findByRole('alert')

    fireEvent.click(screen.getByRole('button', { name: 'Add anyway' }))
    await waitFor(() => expect(mockCreateApplication).toHaveBeenCalledTimes(1))
  })

  it('clears the warning when the company name changes', async () => {
    mockCheckDuplicate.mockResolvedValue(openDuplicate)
    renderModal()
    fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Save application' }))
    await screen.findByRole('alert')

    fireEvent.change(screen.getByPlaceholderText('Spotify'), { target: { value: 'OtherCo' } })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save application' })).toBeInTheDocument()
  })

  it('creates directly when no duplicate exists', async () => {
    mockCheckDuplicate.mockResolvedValue({ duplicate: false, application: null })
    mockCreateApplication.mockResolvedValue(undefined)
    renderModal()
    fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Save application' }))

    await waitFor(() => expect(mockCreateApplication).toHaveBeenCalledTimes(1))
    expect(mockCheckDuplicate).toHaveBeenCalledWith('Acme')
  })
})
