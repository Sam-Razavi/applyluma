import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FitAssessmentPanel from './FitAssessmentPanel'
import { fitAssessmentApi } from '../../../services/fitAssessmentApi'
import type { FitAssessment, FitRequirement } from '../../../types/fitAssessment'

vi.mock('../../../services/fitAssessmentApi', () => ({
  fitAssessmentApi: { status: vi.fn(), latest: vi.fn(), request: vi.fn(), get: vi.fn() },
}))

const api = vi.mocked(fitAssessmentApi)

const requirement = (over: Partial<FitRequirement>): FitRequirement => ({
  id: 'R1',
  text: 'Python',
  category: 'skill',
  importance: 'mandatory',
  ad_quote: 'Python is required',
  ad_quote_found: true,
  status: 'met',
  cv_quote: 'REST API in Python',
  cv_quote_found: true,
  downgraded: false,
  note: 'The CV shows Python in a thesis project.',
  ...over,
})

const assessment = (over: Partial<FitAssessment> = {}): FitAssessment => ({
  id: 'a1',
  raw_job_posting_id: 'job-1',
  job_title: 'Junior Developer',
  company: 'Acme',
  status: 'complete',
  error_message: null,
  recommendation: 'consider',
  limited_information: true,
  model: 'gpt-4o-2024-08-06',
  prompt_version: '1',
  rules_version: '1',
  created_at: '2026-11-13T10:00:00Z',
  result: {
    recommendation: 'consider',
    rule: 'R3',
    reason: '1 of 2 mandatory requirements are met.',
    limited_information: true,
    summary: 'A partial fit.',
    missing_information: ['Whether you have a driving licence'],
    requirements: [
      requirement({}),
      requirement({
        id: 'R2',
        text: 'Driving licence',
        status: 'not_enough_information',
        cv_quote: 'B driving licence',
        cv_quote_found: false,
        downgraded: true,
        ad_quote: 'A driving licence is required',
      }),
      requirement({ id: 'R3', text: 'Docker', importance: 'preferred', status: 'not_met', cv_quote: '', cv_quote_found: null }),
    ],
  },
  ...over,
})

describe('FitAssessmentPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.status.mockResolvedValue({ enabled: true, daily_limit: null, used_today: 0 })
    api.latest.mockResolvedValue(null)
  })

  it('renders nothing for users without access', async () => {
    api.status.mockResolvedValue({ enabled: false, daily_limit: null, used_today: 0 })

    const { container } = render(<FitAssessmentPanel jobId="job-1" />)

    await waitFor(() => expect(api.status).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
    expect(api.latest).not.toHaveBeenCalled()
  })

  it('says what it reads and runs only when asked', async () => {
    api.request.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    const button = await screen.findByRole('button', { name: 'Assess this job' })
    expect(screen.getByText(/Reads this job ad and your default CV, and nothing else/)).toBeInTheDocument()
    expect(screen.getByText(/It can be wrong/)).toBeInTheDocument()
    expect(api.request).not.toHaveBeenCalled()

    await userEvent.click(button)

    expect(api.request).toHaveBeenCalledWith('job-1', false)
    expect(await screen.findByText('Consider')).toBeInTheDocument()
  })

  it('shows a stored assessment with its evidence without a new run', async () => {
    api.latest.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    expect(await screen.findByText('1 of 2 mandatory requirements are met.')).toBeInTheDocument()
    expect(api.request).not.toHaveBeenCalled()
    expect(screen.getByText('Mandatory (2)')).toBeInTheDocument()
    expect(screen.getByText('Preferred (1)')).toBeInTheDocument()
    expect(screen.getByText('From your CV: “REST API in Python”')).toBeInTheDocument()
    expect(screen.getByText(/Limited information/)).toBeInTheDocument()
    expect(screen.getByText('Whether you have a driving licence')).toBeInTheDocument()
    expect(screen.getByText('This is a recommendation. The decision is yours.')).toBeInTheDocument()
    expect(screen.getByText(/Rule R3 · rules v1 · prompt v1/)).toBeInTheDocument()
  })

  it('does not show a quote that is not in the CV as evidence', async () => {
    api.latest.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    expect(
      await screen.findByText(/could not be found in your CV, so it is not counted as met/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/B driving licence/)).not.toBeInTheDocument()
  })

  it('polls while the assessment is running', async () => {
    api.latest.mockResolvedValue(assessment({ status: 'processing', result: null, recommendation: null }))
    api.get.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    expect(await screen.findByRole('status')).toHaveTextContent('Reading the ad and your CV')
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('a1'), { timeout: 4000 })
    expect(await screen.findByText('Consider')).toBeInTheDocument()
  })

  it('offers a retry after a failure, and a forced run on request', async () => {
    api.latest.mockResolvedValue(
      assessment({ status: 'failed', result: null, error_message: 'AI API error: timed out' }),
    )
    api.request.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    expect(await screen.findByText(/could not be completed: AI API error: timed out/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(api.request).toHaveBeenCalledWith('job-1', true)

    await userEvent.click(await screen.findByRole('button', { name: 'Run again' }))
    expect(api.request).toHaveBeenCalledTimes(2)
  })

  it('can be collapsed', async () => {
    api.latest.mockResolvedValue(assessment())

    render(<FitAssessmentPanel jobId="job-1" />)

    await screen.findByText('A partial fit.')
    await userEvent.click(screen.getByRole('button', { name: /AI assessment/ }))

    expect(screen.queryByText('A partial fit.')).not.toBeInTheDocument()
    // The recommendation stays visible in the header.
    expect(screen.getByText('Consider')).toBeInTheDocument()
  })
})
