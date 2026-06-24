import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import AITailor from './AITailor'
import { cvApi, jobApi } from '../services/api'
import { tailorApi } from '../services/tailorApi'
import { coverLetterApi } from '../services/coverLetterApi'

vi.mock('../services/api', () => ({
  cvApi: { list: vi.fn(), download: vi.fn() },
  jobApi: { list: vi.fn() },
}))

vi.mock('../services/tailorApi', () => ({
  tailorApi: { getUsage: vi.fn(), submit: vi.fn(), getStatus: vi.fn(), getPreview: vi.fn(), save: vi.fn() },
}))

vi.mock('../services/coverLetterApi', () => ({
  coverLetterApi: {
    getUsage: vi.fn(),
    submit: vi.fn(),
    getStatus: vi.fn(),
    getPreview: vi.fn(),
    save: vi.fn(),
    list: vi.fn(),
    download: vi.fn(),
    remove: vi.fn(),
  },
}))

vi.mock('../services/applicationsApi', () => ({
  createApplication: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('posthog-js', () => ({ default: { capture: vi.fn() } }))

const cv = { id: 'cv-1', title: 'My CV', is_default: true }
const job = { id: 'job-1', job_title: 'Engineer', company_name: 'Acme' }
const usage = { used_today: 0, daily_limit: 5, resets_at: '2026-06-24T00:00:00Z' }

function setupHappyPath() {
  vi.mocked(cvApi.list).mockResolvedValue([cv] as never)
  vi.mocked(jobApi.list).mockResolvedValue([job] as never)
  vi.mocked(tailorApi.getUsage).mockResolvedValue(usage as never)
  vi.mocked(coverLetterApi.getUsage).mockResolvedValue(usage as never)
  vi.mocked(coverLetterApi.list).mockResolvedValue([] as never)
}

function renderPage() {
  return render(
    <BrowserRouter>
      <AITailor />
    </BrowserRouter>,
  )
}

describe('AITailor unified page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders both toggles and the combined button label by default', async () => {
    setupHappyPath()
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Tailor CV')).toBeInTheDocument()
      expect(screen.getByText('Write cover letter')).toBeInTheDocument()
    })
    expect(screen.getByText('Tailor CV & write cover letter')).toBeInTheDocument()
  })

  it('submits both a tailor job and a cover letter job when both toggles are on', async () => {
    setupHappyPath()
    vi.mocked(tailorApi.submit).mockResolvedValue({ id: 't-1' } as never)
    vi.mocked(coverLetterApi.submit).mockResolvedValue({ id: 'c-1' } as never)
    vi.mocked(tailorApi.getStatus).mockResolvedValue({ status: 'processing' } as never)
    vi.mocked(coverLetterApi.getStatus).mockResolvedValue({ status: 'processing' } as never)

    renderPage()
    await waitFor(() => expect(screen.getByText('Tailor CV & write cover letter')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Tailor CV & write cover letter'))

    await waitFor(() => {
      expect(tailorApi.submit).toHaveBeenCalledTimes(1)
      expect(coverLetterApi.submit).toHaveBeenCalledTimes(1)
    })
  })

  it('only submits a cover letter when the CV toggle is turned off', async () => {
    setupHappyPath()
    vi.mocked(coverLetterApi.submit).mockResolvedValue({ id: 'c-1' } as never)
    vi.mocked(coverLetterApi.getStatus).mockResolvedValue({ status: 'processing' } as never)

    renderPage()
    await waitFor(() => expect(screen.getByText('Tailor CV & write cover letter')).toBeInTheDocument())

    // Turn off the "Tailor CV" toggle card (the title text lives inside the toggle button).
    const toggle = screen.getByText('Tailor CV', { selector: 'span' }).closest('button')
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle as HTMLElement)

    // After turning CV off, the submit button label collapses to "Write cover letter".
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Write cover letter' })).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Write cover letter' }))

    await waitFor(() => {
      expect(coverLetterApi.submit).toHaveBeenCalledTimes(1)
      expect(tailorApi.submit).not.toHaveBeenCalled()
    })
  })
})
