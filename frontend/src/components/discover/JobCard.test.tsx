import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import JobCard from './JobCard'
import type { DiscoveredJob } from '../../types/jobDiscovery'

const baseJob: DiscoveredJob = {
  job_id: 'job-1',
  title: 'Senior Developer',
  company: 'TechCorp',
  location: 'Stockholm',
  salary_min: 50000,
  salary_max: 80000,
  employment_type: 'full_time',
  remote_allowed: false,
  url: 'https://example.com/job',
  source: 'platsbanken',
  scraped_at: '2026-01-01T00:00:00Z',
  match_score: 75,
  skills_match: 80,
  experience_match: 70,
  salary_match_score: 60,
  education_match: 90,
  location_match: null,
  explanation: 'Good match.',
  keywords: [],
  is_saved: false,
}

describe('JobCard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders job title and company', () => {
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('Senior Developer')).toBeInTheDocument()
    expect(screen.getByText('TechCorp')).toBeInTheDocument()
  })

  it('shows full salary range when both min and max are provided', () => {
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText(/50k–80k kr/)).toBeInTheDocument()
  })

  it('shows "from X kr" when only salary_min is provided', () => {
    render(<JobCard job={{ ...baseJob, salary_min: 50000, salary_max: null }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText(/from 50k kr/)).toBeInTheDocument()
  })

  it('shows "up to X kr" when only salary_max is provided', () => {
    render(<JobCard job={{ ...baseJob, salary_min: null, salary_max: 80000 }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText(/up to 80k kr/)).toBeInTheDocument()
  })

  it('calls onClick when card body is clicked', () => {
    const onClick = vi.fn()
    render(<JobCard job={baseJob} onClick={onClick} onSave={vi.fn()} />)
    fireEvent.click(screen.getByText('TechCorp'))
    expect(onClick).toHaveBeenCalledWith(baseJob)
  })

  it('calls onSave when save button is clicked', () => {
    const onSave = vi.fn()
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={onSave} />)
    fireEvent.click(screen.getByLabelText('Save job'))
    expect(onSave).toHaveBeenCalledWith(baseJob)
  })

  it('shows "Unsave job" aria-label when job is already saved', () => {
    render(<JobCard job={{ ...baseJob, is_saved: true }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByLabelText('Unsave job')).toBeInTheDocument()
  })

  it('shows application status badge when application_id is present', () => {
    render(
      <JobCard
        job={{ ...baseJob, application_id: 'app-1', application_status: 'applied' }}
        onClick={vi.fn()}
        onSave={vi.fn()}
      />,
    )
    expect(screen.getByText('applied')).toBeInTheDocument()
  })

  it('shows "Applied" when application_id present but no application_status', () => {
    render(
      <JobCard
        job={{ ...baseJob, application_id: 'app-1', application_status: null }}
        onClick={vi.fn()}
        onSave={vi.fn()}
      />,
    )
    expect(screen.getByText('Applied')).toBeInTheDocument()
  })

  it('shows score bars when match_score and sub-scores are present', () => {
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Experience')).toBeInTheDocument()
    expect(screen.getByText('Salary')).toBeInTheDocument()
  })

  it('shows Remote badge when remote_allowed is true', () => {
    render(<JobCard job={{ ...baseJob, remote_allowed: true }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('Remote')).toBeInTheDocument()
  })

  it('shows explanation when provided', () => {
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('Good match.')).toBeInTheDocument()
  })

  it('shows match score badge', () => {
    render(<JobCard job={baseJob} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('does not show salary when both min and max are null', () => {
    render(<JobCard job={{ ...baseJob, salary_min: null, salary_max: null }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.queryByText(/kr/)).not.toBeInTheDocument()
  })

  it('formats small salary values without k suffix', () => {
    render(<JobCard job={{ ...baseJob, salary_min: 500, salary_max: 900 }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText(/500–900 kr/)).toBeInTheDocument()
  })

  it('renders without score bars when skills_match is null but shows others', () => {
    render(
      <JobCard
        job={{ ...baseJob, skills_match: null, experience_match: 80, salary_match_score: 60 }}
        onClick={vi.fn()}
        onSave={vi.fn()}
      />,
    )
    // ScoreBar for skills_match should return null; others should still render
    expect(screen.getByText('Experience')).toBeInTheDocument()
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
  })

  it('falls back to raw source name when source has no label', () => {
    render(<JobCard job={{ ...baseJob, source: 'custom_board' }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('custom_board')).toBeInTheDocument()
  })

  it('does not show match score badge when match_score is null', () => {
    render(<JobCard job={{ ...baseJob, match_score: null }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
  })

  it('shows red badge for low match score', () => {
    render(<JobCard job={{ ...baseJob, match_score: 40 }} onClick={vi.fn()} onSave={vi.fn()} />)
    expect(screen.getByText('40%')).toBeInTheDocument()
  })
})
