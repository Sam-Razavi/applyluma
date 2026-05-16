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

  it('shows error toast when job loading fails', async () => {
    vi.mocked(jobDiscoveryApi.fetchDiscoveredJobs).mockRejectedValue(new Error('Network error'))
    renderDiscover()
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load jobs')
    })
  })
})
