import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import SavedJobs from './SavedJobs'
import * as jobDiscoveryApi from '../services/jobDiscoveryApi'
import toast from 'react-hot-toast'

vi.mock('../services/jobDiscoveryApi', () => ({
  fetchSavedJobs: vi.fn(),
  updateSavedJob: vi.fn(),
  deleteSavedJob: vi.fn(),
  fetchJobDetail: vi.fn(),
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
  is_saved: true,
}

const mockSaved = {
  id: 'saved-1',
  user_id: 'user-1',
  raw_job_posting_id: 'job-1',
  list_name: 'Dream roles',
  notes: 'Great company culture',
  starred: false,
  created_at: '2026-05-15T00:00:00Z',
  updated_at: '2026-05-15T00:00:00Z',
  job: mockJob,
}

function renderPage() {
  return render(
    <BrowserRouter>
      <SavedJobs />
    </BrowserRouter>,
  )
}

describe('SavedJobs page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page heading', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([])
    renderPage()
    expect(screen.getByText('Saved Jobs')).toBeInTheDocument()
  })

  it('shows empty state when no saved jobs', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No saved jobs yet')).toBeInTheDocument()
    })
  })

  it('renders saved job cards after loading', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Senior Python Developer')).toBeInTheDocument()
      expect(screen.getByText('TechAB')).toBeInTheDocument()
    })
  })

  it('shows job notes on card', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Great company culture')).toBeInTheDocument()
    })
  })

  it('shows list_name badge', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Dream roles')).toBeInTheDocument()
    })
  })

  it('stars a job when star button clicked', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    vi.mocked(jobDiscoveryApi.updateSavedJob).mockResolvedValue({ ...mockSaved, starred: true })
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Star job')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Star job'))

    await waitFor(() => {
      expect(jobDiscoveryApi.updateSavedJob).toHaveBeenCalledWith('saved-1', { starred: true })
    })
  })

  it('deletes a saved job when delete button clicked', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    vi.mocked(jobDiscoveryApi.deleteSavedJob).mockResolvedValue()
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Remove saved job')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Remove saved job'))

    await waitFor(() => {
      expect(jobDiscoveryApi.deleteSavedJob).toHaveBeenCalledWith('saved-1')
      expect(toast.success).toHaveBeenCalledWith('Removed from saved jobs')
    })
  })

  it('removes card from list after delete', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    vi.mocked(jobDiscoveryApi.deleteSavedJob).mockResolvedValue()
    renderPage()

    await waitFor(() => expect(screen.getByText('Senior Python Developer')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Remove saved job'))

    await waitFor(() => {
      expect(screen.queryByText('Senior Python Developer')).not.toBeInTheDocument()
    })
  })

  it('shows collection tabs when multiple list_names exist', async () => {
    const second = { ...mockSaved, id: 'saved-2', list_name: 'Backup options' }
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved, second])
    renderPage()

    await waitFor(() => {
      // Collection tab buttons (not the card badges)
      const tabs = screen.getAllByRole('button', { name: /Dream roles|Backup options|All/ })
      expect(tabs.length).toBeGreaterThanOrEqual(3)
    })
  })

  it('shows error toast when loading fails', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load saved jobs')
    })
  })

  it('shows job count in heading', async () => {
    vi.mocked(jobDiscoveryApi.fetchSavedJobs).mockResolvedValue([mockSaved])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('1 saved job')).toBeInTheDocument()
    })
  })
})
