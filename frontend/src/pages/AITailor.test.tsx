import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AITailor from './AITailor'
import { cvApi, jobApi } from '../services/api'
import { tailorApi } from '../services/tailorApi'
import toast from 'react-hot-toast'

vi.mock('../services/api', () => ({
  cvApi: { list: vi.fn(), download: vi.fn() },
  jobApi: { list: vi.fn() },
}))

vi.mock('../services/tailorApi', () => ({
  tailorApi: {
    getUsage: vi.fn(),
    submit: vi.fn(),
    getStatus: vi.fn(),
    getPreview: vi.fn(),
    save: vi.fn(),
  },
}))

vi.mock('../services/jobDiscoveryApi', () => ({
  fetchJobDetail: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const mockCv = {
  id: 'cv-1',
  user_id: 'user-1',
  title: 'My CV',
  filename: 'my-cv.pdf',
  content: null,
  file_url: null,
  file_size: null,
  is_default: true,
  is_tailored: false,
  parent_cv_id: null,
  tailor_job_id: null,
  created_at: '2026-05-15T00:00:00Z',
  updated_at: '2026-05-15T00:00:00Z',
}

const mockJobDesc = {
  id: 'job-1',
  user_id: 'user-1',
  company_name: 'TechCo',
  job_title: 'Software Engineer',
  description: 'A great job',
  url: null,
  keywords: [],
  created_at: '2026-05-15T00:00:00Z',
  updated_at: '2026-05-15T00:00:00Z',
}

const mockUsage = { used_today: 0, daily_limit: 1, resets_at: '2026-05-18T00:00:00Z' }

const mockTailorJob = {
  id: 'tailor-1',
  cv_id: 'cv-1',
  job_description_id: 'job-1',
  intensity: 'medium' as const,
  status: 'pending' as const,
  error_message: null,
  language: null,
  output_cv_id: null,
  created_at: '2026-05-15T00:00:00Z',
  updated_at: '2026-05-15T00:00:00Z',
}

const mockPreview = {
  job_id: 'tailor-1',
  language: 'en',
  sections: [
    {
      section_id: 'sec-1',
      section_name: 'Summary',
      original: 'Old summary text',
      tailored: 'New summary text',
      changes: ['Rewrote opening'],
    },
  ],
  meta: {
    keywords_added: ['Python', 'FastAPI'],
    keywords_already_present: ['SQL'],
    intensity_applied: 'medium',
  },
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/ai-tailor', state: null }]}>
      <AITailor />
    </MemoryRouter>,
  )
}

describe('AITailor page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cvApi.list).mockResolvedValue([mockCv])
    vi.mocked(jobApi.list).mockResolvedValue([mockJobDesc])
    vi.mocked(tailorApi.getUsage).mockResolvedValue(mockUsage)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders page heading', () => {
    renderPage()
    expect(screen.getByText('AI CV Tailor')).toBeInTheDocument()
  })

  it('shows Tailor CV button in select step', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: /Tailor CV/i })).toBeInTheDocument())
  })

  it('shows usage banner after initial load', async () => {
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/0 of 1 tailoring runs used today/)).toBeInTheDocument(),
    )
  })

  it('disables submit button when no CVs are available', async () => {
    vi.mocked(cvApi.list).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Tailor CV/i })).toBeDisabled()
    })
  })

  it('shows at-limit message when daily limit is reached', async () => {
    vi.mocked(tailorApi.getUsage).mockResolvedValue({
      used_today: 1,
      daily_limit: 1,
      resets_at: '2026-05-18T00:00:00Z',
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Daily tailoring limit reached/)).toBeInTheDocument(),
    )
  })

  it('calls tailorApi.submit with correct payload and shows processing step', async () => {
    vi.mocked(tailorApi.submit).mockResolvedValue(mockTailorJob)
    vi.mocked(tailorApi.getStatus).mockResolvedValue({
      id: 'tailor-1',
      status: 'processing',
      error_message: null,
      language: null,
      output_cv_id: null,
    })

    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Tailor CV/i })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Tailor CV/i }))

    await waitFor(() => {
      expect(tailorApi.submit).toHaveBeenCalledWith(
        expect.objectContaining({ cv_id: 'cv-1', job_description_id: 'job-1' }),
      )
    })
    await waitFor(() => expect(screen.getByText('Tailoring your CV')).toBeInTheDocument())
  })

  it('transitions to preview step after polling returns complete', async () => {
    vi.mocked(tailorApi.submit).mockResolvedValue(mockTailorJob)
    vi.mocked(tailorApi.getStatus).mockResolvedValue({
      id: 'tailor-1',
      status: 'complete',
      error_message: null,
      language: 'en',
      output_cv_id: null,
    })
    vi.mocked(tailorApi.getPreview).mockResolvedValue(mockPreview)
    vi.spyOn(window, 'setInterval').mockImplementation((fn) => {
      void Promise.resolve().then(() => (fn as () => void)())
      return 0 as unknown as ReturnType<typeof setInterval>
    })
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)

    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Tailor CV/i })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Tailor CV/i }))

    await waitFor(() => expect(screen.getByText('Review section changes')).toBeInTheDocument())
  })

  it('toggles section from accepted to rejected in preview step', async () => {
    vi.mocked(tailorApi.submit).mockResolvedValue(mockTailorJob)
    vi.mocked(tailorApi.getStatus).mockResolvedValue({
      id: 'tailor-1',
      status: 'complete',
      error_message: null,
      language: 'en',
      output_cv_id: null,
    })
    vi.mocked(tailorApi.getPreview).mockResolvedValue(mockPreview)
    vi.spyOn(window, 'setInterval').mockImplementation((fn) => {
      void Promise.resolve().then(() => (fn as () => void)())
      return 0 as unknown as ReturnType<typeof setInterval>
    })
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)

    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Tailor CV/i })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Tailor CV/i }))
    await waitFor(() => expect(screen.getByText('1 of 1 accepted')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Accepted/i }))
    expect(screen.getByText('0 of 1 accepted')).toBeInTheDocument()
  })

  it('calls tailorApi.save and transitions to done step', async () => {
    vi.mocked(tailorApi.submit).mockResolvedValue(mockTailorJob)
    vi.mocked(tailorApi.getStatus).mockResolvedValue({
      id: 'tailor-1',
      status: 'complete',
      error_message: null,
      language: 'en',
      output_cv_id: null,
    })
    vi.mocked(tailorApi.getPreview).mockResolvedValue(mockPreview)
    vi.mocked(tailorApi.save).mockResolvedValue({ cv_id: 'cv-2', title: 'Tailored CV', file_url: null })
    vi.spyOn(window, 'setInterval').mockImplementation((fn) => {
      void Promise.resolve().then(() => (fn as () => void)())
      return 0 as unknown as ReturnType<typeof setInterval>
    })
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)

    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Tailor CV/i })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Tailor CV/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Save tailored PDF/i })).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Save tailored PDF/i }))

    await waitFor(() => {
      expect(tailorApi.save).toHaveBeenCalled()
      expect(screen.getByText('Tailored CV saved')).toBeInTheDocument()
    })
  })

  it('shows API error detail in toast when submit fails', async () => {
    const err = { response: { data: { detail: 'No CV found for user' } } }
    vi.mocked(tailorApi.submit).mockRejectedValue(err)

    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Tailor CV/i })).not.toBeDisabled(),
    )

    fireEvent.click(screen.getByRole('button', { name: /Tailor CV/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No CV found for user')
    })
  })

  it('shows generic error toast when initial data load fails', async () => {
    vi.mocked(cvApi.list).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load tailoring data')
    })
  })
})
