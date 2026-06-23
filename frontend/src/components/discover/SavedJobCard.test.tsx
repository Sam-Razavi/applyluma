import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import SavedJobCard from './SavedJobCard'
import type { SavedJob } from '../../types/jobDiscovery'

const mockSavedJob: SavedJob = {
  id: 'saved-1',
  user_id: 'user-1',
  raw_job_posting_id: 'job-1',
  list_name: null,
  notes: null,
  starred: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  job: {
    job_id: 'job-1',
    title: 'Backend Engineer',
    company: 'Acme Corp',
    location: 'Stockholm',
    salary_min: 45000,
    salary_max: 70000,
    employment_type: 'full_time',
    remote_allowed: false,
    is_remote: false,
    url: 'https://example.com/job',
    source: 'Platsbanken',
    scraped_at: '2026-01-01T00:00:00Z',
    match_score: null,
    skills_match: null,
    experience_match: null,
    salary_match_score: null,
    education_match: null,
    location_match: null,
    explanation: null,
    keywords: [],
    is_saved: true,
  },
}

function renderCard(props: Partial<React.ComponentProps<typeof SavedJobCard>> = {}) {
  return render(
    <BrowserRouter>
      <SavedJobCard
        saved={mockSavedJob}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
        {...props}
      />
    </BrowserRouter>,
  )
}

describe('SavedJobCard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders job title and company', () => {
    renderCard()
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })

  it('shows salary range when both min and max provided', () => {
    renderCard()
    expect(screen.getByText(/45k–70k kr/)).toBeInTheDocument()
  })

  it('shows "from X kr" when only salary_min is provided', () => {
    renderCard({ saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, salary_min: 45000, salary_max: null } } })
    expect(screen.getByText(/from 45k kr/)).toBeInTheDocument()
  })

  it('shows "up to X kr" when only salary_max is provided', () => {
    renderCard({ saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, salary_min: null, salary_max: 70000 } } })
    expect(screen.getByText(/up to 70k kr/)).toBeInTheDocument()
  })

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn()
    renderCard({ onClick })
    fireEvent.click(screen.getByText('Backend Engineer'))
    expect(onClick).toHaveBeenCalledWith('job-1')
  })

  it('calls onStar when star button clicked', () => {
    const onStar = vi.fn()
    renderCard({ onStar })
    fireEvent.click(screen.getByLabelText('Star job'))
    expect(onStar).toHaveBeenCalledWith('saved-1', true)
  })

  it('shows Unstar label when job is starred', () => {
    renderCard({ saved: { ...mockSavedJob, starred: true } })
    expect(screen.getByLabelText('Unstar job')).toBeInTheDocument()
  })

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn()
    renderCard({ onDelete })
    fireEvent.click(screen.getByLabelText('Remove saved job'))
    expect(onDelete).toHaveBeenCalledWith('saved-1')
  })

  it('renders Add to Applications button when prop provided', () => {
    renderCard({ onAddToApplications: vi.fn() })
    expect(screen.getByText('Add to Applications')).toBeInTheDocument()
  })

  it('calls onAddToApplications when that button is clicked', () => {
    const onAdd = vi.fn()
    renderCard({ onAddToApplications: onAdd })
    fireEvent.click(screen.getByText('Add to Applications'))
    expect(onAdd).toHaveBeenCalledWith(mockSavedJob)
  })

  it('shows Adding... and disables button when addingToApplications is true', () => {
    renderCard({ onAddToApplications: vi.fn(), addingToApplications: true })
    expect(screen.getByText('Adding...')).toBeInTheDocument()
    expect(screen.getByText('Adding...').closest('button')).toBeDisabled()
  })

  it('hides Add to Applications when job already has application status', () => {
    renderCard({
      saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, application_status: 'applied' } },
      onAddToApplications: vi.fn(),
    })
    expect(screen.queryByText('Add to Applications')).not.toBeInTheDocument()
  })

  it('shows application status badge when present', () => {
    renderCard({
      saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, application_status: 'phone_screen' } },
    })
    expect(screen.getByText('phone screen')).toBeInTheDocument()
  })

  it('always shows the combined tailor button', () => {
    renderCard()
    expect(screen.getByText('Tailor CV + Cover Letter')).toBeInTheDocument()
  })

  it('shows notes when present', () => {
    renderCard({ saved: { ...mockSavedJob, notes: 'Follow up next week' } })
    expect(screen.getByText('Follow up next week')).toBeInTheDocument()
  })

  it('shows Remote badge when remote_allowed is true', () => {
    renderCard({ saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, remote_allowed: true } } })
    expect(screen.getByText('Remote')).toBeInTheDocument()
  })

  it('shows "Unknown job" when job is null', () => {
    renderCard({ saved: { ...mockSavedJob, job: null } })
    expect(screen.getByText('Unknown job')).toBeInTheDocument()
  })

  it('shows no salary when both salary values are null', () => {
    renderCard({ saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, salary_min: null, salary_max: null } } })
    expect(screen.queryByText(/kr/)).not.toBeInTheDocument()
  })

  it('formats small salary values without k suffix', () => {
    renderCard({ saved: { ...mockSavedJob, job: { ...mockSavedJob.job!, salary_min: 800, salary_max: 950 } } })
    expect(screen.getByText(/800–950 kr/)).toBeInTheDocument()
  })
})
