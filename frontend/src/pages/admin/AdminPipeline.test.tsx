import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import AdminPipeline from './AdminPipeline'
import { adminApi } from '../../services/adminApi'

vi.mock('../../services/adminApi', () => ({
  adminApi: {
    getPipelineHealth: vi.fn(),
    getJobsOverTime: vi.fn(),
    getJobsBySource: vi.fn(),
    getPipelineMetrics: vi.fn(),
  },
}))

function renderAdminPipeline() {
  return render(
    <BrowserRouter>
      <AdminPipeline />
    </BrowserRouter>,
  )
}

describe('AdminPipeline page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminApi.getPipelineHealth).mockResolvedValue({
      raw_job_postings: {
        name: 'raw_job_postings',
        count: 120,
        last_run: '2026-06-16T08:00:00Z',
        healthy: true,
      },
      extracted_keywords: {
        name: 'extracted_keywords',
        count: 450,
        last_run: '2026-06-16T08:30:00Z',
        healthy: true,
      },
      job_market_metrics: {
        name: 'job_market_metrics',
        count: 3,
        last_run: null,
        healthy: false,
      },
      sources: [
        {
          source: 'remotive',
          count: 30,
          last_run: '2026-06-16T09:00:00Z',
          healthy: true,
        },
      ],
    })
    vi.mocked(adminApi.getJobsOverTime).mockResolvedValue([{ date: '2026-06-16', count: 5 }])
    vi.mocked(adminApi.getJobsBySource).mockResolvedValue([{ source: 'remotive', count: 30 }])
    vi.mocked(adminApi.getPipelineMetrics).mockResolvedValue({
      metric_date: '2026-06-16',
      total_jobs_scraped: 120,
      remote_percentage: 42.5,
      top_skills: [{ skill: 'Python', count: 12 }],
      top_companies: [{ company: 'ApplyLuma', count: 4 }],
    })
  })

  it('renders pipeline health and remote percentage', async () => {
    renderAdminPipeline()

    await waitFor(() => {
      expect(screen.getAllByText('Healthy').length).toBeGreaterThan(0)
      expect(screen.getByText('42.5%')).toBeInTheDocument()
    })
    expect(screen.getByText('Raw job postings')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
  })

  it('shows an error banner when loading fails', async () => {
    vi.mocked(adminApi.getPipelineHealth).mockRejectedValue(new Error('Network error'))

    renderAdminPipeline()

    await waitFor(() => {
      expect(screen.getByText('Failed to load pipeline health')).toBeInTheDocument()
    })
  })
})
