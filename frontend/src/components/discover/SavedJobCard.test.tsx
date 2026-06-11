import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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
    url: 'https://example.com/job',
    source: 'platsbanken',
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

describe('SavedJobCard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders job title and company', () => {
    render(
      <SavedJobCard saved={mockSavedJob} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })

  it('shows salary range when both min and max provided', () => {
    render(
      <SavedJobCard saved={mockSavedJob} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByText(/45k–70k kr/)).toBeInTheDocument()
  })

  it('shows "from X kr" when only salary_min is provided', () => {
    const s = {
      ...mockSavedJob,
      job: { ...mockSavedJob.job!, salary_min: 45000, salary_max: null },
    }
    render(<SavedJobCard saved={s} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText(/from 45k kr/)).toBeInTheDocument()
  })

  it('shows "up to X kr" when only salary_max is provided', () => {
    const s = {
      ...mockSavedJob,
      job: { ...mockSavedJob.job!, salary_min: null, salary_max: 70000 },
    }
    render(<SavedJobCard saved={s} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText(/up to 70k kr/)).toBeInTheDocument()
  })

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn()
    render(<SavedJobCard saved={mockSavedJob} onClick={onClick} onStar={vi.fn()} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByText('Backend Engineer'))
    expect(onClick).toHaveBeenCalledWith('job-1')
  })

  it('calls onStar when star button clicked', () => {
    const onStar = vi.fn()
    render(
      <SavedJobCard saved={mockSavedJob} onClick={vi.fn()} onStar={onStar} onDelete={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Star job'))
    expect(onStar).toHaveBeenCalledWith('saved-1', true)
  })

  it('shows Unstar label when job is starred', () => {
    render(
      <SavedJobCard
        saved={{ ...mockSavedJob, starred: true }}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByLabelText('Unstar job')).toBeInTheDocument()
  })

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn()
    render(
      <SavedJobCard saved={mockSavedJob} onClick={vi.fn()} onStar={vi.fn()} onDelete={onDelete} />,
    )
    fireEvent.click(screen.getByLabelText('Remove saved job'))
    expect(onDelete).toHaveBeenCalledWith('saved-1')
  })

  it('renders onAddToDescriptions button when prop provided', () => {
    const onAdd = vi.fn()
    render(
      <SavedJobCard
        saved={mockSavedJob}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
        onAddToDescriptions={onAdd}
      />,
    )
    expect(screen.getByLabelText('Add to job descriptions')).toBeInTheDocument()
  })

  it('calls onAddToDescriptions when that button is clicked', () => {
    const onAdd = vi.fn()
    render(
      <SavedJobCard
        saved={mockSavedJob}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
        onAddToDescriptions={onAdd}
      />,
    )
    fireEvent.click(screen.getByLabelText('Add to job descriptions'))
    expect(onAdd).toHaveBeenCalledWith(mockSavedJob)
  })

  it('shows spinner and disables button when addingToDescriptions is true', () => {
    render(
      <SavedJobCard
        saved={mockSavedJob}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
        onAddToDescriptions={vi.fn()}
        addingToDescriptions={true}
      />,
    )
    const btn = screen.getByLabelText('Add to job descriptions')
    expect(btn).toBeDisabled()
  })

  it('shows notes when present', () => {
    render(
      <SavedJobCard
        saved={{ ...mockSavedJob, notes: 'Follow up next week' }}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByText('Follow up next week')).toBeInTheDocument()
  })

  it('shows Remote badge when remote_allowed is true', () => {
    const s = { ...mockSavedJob, job: { ...mockSavedJob.job!, remote_allowed: true } }
    render(<SavedJobCard saved={s} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('Remote')).toBeInTheDocument()
  })

  it('shows "Unknown job" when job is null', () => {
    render(
      <SavedJobCard
        saved={{ ...mockSavedJob, job: null }}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByText('Unknown job')).toBeInTheDocument()
  })

  it('shows no salary when both salary values are null', () => {
    const s = {
      ...mockSavedJob,
      job: { ...mockSavedJob.job!, salary_min: null, salary_max: null },
    }
    render(<SavedJobCard saved={s} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.queryByText(/kr/)).not.toBeInTheDocument()
  })

  it('formats small salary values without k suffix', () => {
    const s = {
      ...mockSavedJob,
      job: { ...mockSavedJob.job!, salary_min: 800, salary_max: 950 },
    }
    render(<SavedJobCard saved={s} onClick={vi.fn()} onStar={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText(/800–950 kr/)).toBeInTheDocument()
  })

  it('shows list_name badge when present', () => {
    render(
      <SavedJobCard
        saved={{ ...mockSavedJob, list_name: 'Dream Jobs' }}
        onClick={vi.fn()}
        onStar={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByText('Dream Jobs')).toBeInTheDocument()
  })
})
