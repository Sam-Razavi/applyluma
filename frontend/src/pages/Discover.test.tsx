import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Discover from './Discover'
import * as jobDiscoveryApi from '../services/jobDiscoveryApi'
import toast from 'react-hot-toast'

vi.mock('../services/jobDiscoveryApi', () => ({
  fetchDiscoveredJobs: vi.fn(),
  fetchJobDetail: vi.fn(),
  saveJob: vi.fn(),
  deleteSavedJob: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const mockJob = {
  job_id: 'job-1',
  title: 'Senior Python Developer',
  company: 'TechAB',
  location: 'Stockholm',
  salary_min: 60000,
  salary_max: 90000,
  employment_type: 'full_time',
  remote_allowed: false,
  url: 'https://example.com/job/1',
  source: 'platsbanken',
  scraped_at: '2026-05-15T00:00:00Z',
  match_score: 87,
  skills_match: 90,
  experience_match: 85,
  salary_match_score: 80,
  education_match: 100,
  location_match: 80,
  explanation: 'You have 5/6 required skills.',
  keywords: [],
  is_saved: false,
}

function renderDiscover() {
  return render(
    <BrowserRouter>
      <Discover />
    </BrowserRouter>,
  )
}

describe('Discover page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page heading', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([])
    renderDiscover()
    expect(screen.getByText('Discover Jobs')).toBeInTheDocument()
  })

  it('shows job cards after loading', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([mockJob])
    renderDiscover()
    await waitFor(() => {
      expect(screen.getByText('Senior Python Developer')).toBeInTheDocument()
      expect(screen.getByText('TechAB')).toBeInTheDocument()
    })
  })

  it('shows empty state when no jobs returned', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([])
    renderDiscover()
    await waitFor(() => {
      expect(screen.getByText('No jobs found')).toBeInTheDocument()
    })
  })

  it('shows match score badge on job card', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([mockJob])
    renderDiscover()
    await waitFor(() => {
      expect(screen.getByText('87%')).toBeInTheDocument()
    })
  })

  it('calls saveJob when save button clicked', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([mockJob])
    vi.mocked(jobDiscoveryApi.saveJob).mockResolvedValue({
      id: 'saved-1',
      user_id: 'user-1',
      raw_job_posting_id: 'job-1',
      list_name: null,
      notes: null,
      starred: false,
      created_at: '2026-05-15T00:00:00Z',
      updated_at: '2026-05-15T00:00:00Z',
      job: null,
    })
    renderDiscover()

    await waitFor(() => expect(screen.getByText('Senior Python Developer')).toBeInTheDocument())

    const saveBtn = screen.getByLabelText('Save job')
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(jobDiscoveryApi.saveJob).toHaveBeenCalledWith({ job_id: 'job-1' })
      expect(toast.success).toHaveBeenCalledWith('Job saved!')
    })
  })

  it('shows error state UI when initial job load fails', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockRejectedValue(new Error('Network error'))
    renderDiscover()
    await waitFor(() => {
      expect(screen.getByText('Failed to load jobs')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
    })
  })

  it('retries loading when Try again is clicked', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce([mockJob])
    renderDiscover()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(screen.getByText('Senior Python Developer')).toBeInTheDocument())
  })

  it('calls deleteSavedJob when save button clicked on an already-saved job', async () => {
    const savedJob = { ...mockJob, is_saved: true, saved_job_id: 'saved-1' }
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockResolvedValue([savedJob])
    vi.mocked(jobDiscoveryApi.deleteSavedJob).mockResolvedValue(undefined)
    renderDiscover()

    await waitFor(() => expect(screen.getByText('Senior Python Developer')).toBeInTheDocument())

    fireEvent.click(screen.getByLabelText('Unsave job'))

    await waitFor(() => {
      expect(jobDiscoveryApi.deleteSavedJob).toHaveBeenCalledWith('saved-1')
    })
  })
})
