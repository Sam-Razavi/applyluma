import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PersonalAnalytics from './PersonalAnalytics'
import * as api from '../../services/applicationsApi'
import type { ApplicationAnalytics, ApplicationInsights } from '../../types/application'

vi.mock('../../services/applicationsApi')
// recharts needs layout that jsdom lacks; the charts are covered elsewhere.
vi.mock('./FunnelChart', () => ({ default: () => <div>funnel</div> }))
vi.mock('./ApplicationsOverTimeChart', () => ({ default: () => <div>over-time</div> }))
vi.mock('./SourceBreakdownChart', () => ({ default: () => <div>sources</div> }))

const analytics: ApplicationAnalytics = {
  funnel: [{ status: 'applied', count: 3 }],
  response_rate: 0.5,
  offer_rate: 0.1,
  average_response_days: 4,
  weekly_counts: [{ week_start: '2026-11-09', count: 3 }],
  top_sources: [{ source: 'linkedin', count: 3 }],
  salary_distribution: [{ bucket: '30-60k', count: 2 }],
}

const insights: ApplicationInsights = {
  total: 5,
  submitted: 3,
  active: 3,
  closed: 0,
  wishlist: 2,
  applied_last_7d: 2,
  applied_prev_7d: 1,
  applied_last_30d: 3,
  interview_rate: 0.33,
  awaiting_reply: 1,
  awaiting_reply_days: 14,
  daily_counts: [
    { date: '2026-11-15', count: 0 },
    { date: '2026-11-16', count: 1 },
    { date: '2026-11-17', count: 2 },
  ],
  stage_reach: [
    { stage: 'applied', count: 3, rate: 1 },
    { stage: 'phone_screen', count: 1, rate: 0.33 },
    { stage: 'interview', count: 1, rate: 0.33 },
    { stage: 'offer', count: 0, rate: 0 },
  ],
  work_modes: [{ label: 'Remote', count: 2 }],
  top_locations: [{ label: 'Stockholm', count: 2 }],
  top_companies: [],
  weekday_counts: [
    { label: 'Mon', count: 2 },
    { label: 'Tue', count: 1 },
  ],
  source_performance: [{ source: 'linkedin', applications: 3, responses: 1, response_rate: 0.33 }],
  cv_performance: [{ cv_id: 'c1', title: 'Main CV', applications: 3, responses: 1, response_rate: 0.33 }],
  upcoming: [
    {
      application_id: 'a1',
      company_name: 'Acme',
      job_title: 'Developer',
      kind: 'interview',
      date: '2026-11-20T10:00:00Z',
      days_away: 3,
    },
  ],
  salary_median: 45000,
  salary_min: 40000,
  salary_max: 50000,
  salary_sample: 2,
}

function renderStats() {
  return render(
    <MemoryRouter>
      <PersonalAnalytics />
    </MemoryRouter>,
  )
}

describe('PersonalAnalytics', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the plain-language summary, tiles and detail panels', async () => {
    vi.mocked(api.fetchApplicationAnalytics).mockResolvedValue(analytics)
    vi.mocked(api.fetchApplicationInsights).mockResolvedValue(insights)
    renderStats()

    expect(await screen.findByText('Your search at a glance')).toBeInTheDocument()
    expect(screen.getByText(/You have sent 3 applications so far, 2 of them in the last 7 days/)).toBeInTheDocument()
    expect(screen.getByText('Sent per day')).toBeInTheDocument()
    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText(/3 applications sent in the last 7 days/)).toBeInTheDocument()
    expect(screen.getByText('Waiting for a reply')).toBeInTheDocument()
    expect(screen.getByText('Results by CV')).toBeInTheDocument()
    expect(screen.getByText('Main CV')).toBeInTheDocument()
    expect(screen.getByText('Acme')).toBeInTheDocument()
    expect(screen.getByText('Stockholm')).toBeInTheDocument()
    expect(screen.getByText(/Typical pay across 2 applications/)).toBeInTheDocument()
  })

  it('still shows the original charts when insights fail to load', async () => {
    vi.mocked(api.fetchApplicationAnalytics).mockResolvedValue(analytics)
    vi.mocked(api.fetchApplicationInsights).mockRejectedValue(new Error('boom'))
    renderStats()

    await waitFor(() => expect(screen.getByText('funnel')).toBeInTheDocument())
    expect(screen.queryByText('Your search at a glance')).not.toBeInTheDocument()
  })

  it('shows an error when the base analytics fail', async () => {
    vi.mocked(api.fetchApplicationAnalytics).mockRejectedValue(new Error('boom'))
    vi.mocked(api.fetchApplicationInsights).mockResolvedValue(insights)
    renderStats()

    expect(await screen.findByText('Could not load application analytics')).toBeInTheDocument()
  })

  it('shows the empty state with no applications', async () => {
    vi.mocked(api.fetchApplicationAnalytics).mockResolvedValue({
      ...analytics,
      funnel: [{ status: 'applied', count: 0 }],
    })
    vi.mocked(api.fetchApplicationInsights).mockResolvedValue(insights)
    renderStats()

    expect(await screen.findByText('No personal stats yet')).toBeInTheDocument()
  })
})
