import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Jobs from './Jobs'
import * as api from '../services/api'
import toast from 'react-hot-toast'

vi.mock('../services/api', () => ({
  jobApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    scrapeUrl: vi.fn(),
    saveFromDiscover: vi.fn(),
  },
  CreateJobDescriptionRequest: {},
}))

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
}))

const mockJd = {
  id: 'jd-1',
  user_id: 'user-1',
  source_raw_job_posting_id: 'job-1',
  company_name: 'TechAB',
  job_title: 'Senior Python Developer',
  description: 'Build scalable APIs with Python and FastAPI.',
  url: 'https://example.com/job/1',
  keywords: ['Python', 'FastAPI', 'PostgreSQL'],
  starred: false,
  notes: 'Great company culture',
  list_name: 'Dream roles',
  created_at: '2026-05-15T00:00:00Z',
  updated_at: '2026-05-15T00:00:00Z',
}

function renderPage() {
  return render(
    <BrowserRouter>
      <Jobs />
    </BrowserRouter>,
  )
}

describe('Jobs page (unified My Jobs)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page heading', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([])
    renderPage()
    expect(screen.getByText('My Jobs')).toBeInTheDocument()
  })

  it('shows empty state when no jobs', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No jobs yet')).toBeInTheDocument()
    })
  })

  it('renders job cards after loading', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Senior Python Developer')).toBeInTheDocument()
      expect(screen.getByText('TechAB')).toBeInTheDocument()
    })
  })

  it('shows keywords on card', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Python')).toBeInTheDocument()
      expect(screen.getByText('FastAPI')).toBeInTheDocument()
    })
  })

  it('shows job notes on card', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Great company culture')).toBeInTheDocument()
    })
  })

  it('shows list_name badge', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Dream roles')).toBeInTheDocument()
    })
  })

  it('stars a job when star button clicked', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    vi.mocked(api.jobApi.update).mockResolvedValue({ ...mockJd, starred: true })
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Star job')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Star job'))

    await waitFor(() => {
      expect(api.jobApi.update).toHaveBeenCalledWith('jd-1', { starred: true })
    })
  })

  it('deletes a job after confirmation', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    vi.mocked(api.jobApi.remove).mockResolvedValue(undefined)
    renderPage()

    await waitFor(() => expect(screen.getByText('Senior Python Developer')).toBeInTheDocument())

    const deleteButtons = screen.getAllByRole('button').filter((btn) =>
      btn.querySelector('.h-4.w-4') && btn.className.includes('hover:text-red-300'),
    )
    fireEvent.click(deleteButtons[0])

    await waitFor(() => expect(screen.getByText('Delete Job')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => {
      expect(api.jobApi.remove).toHaveBeenCalledWith('jd-1')
      expect(toast.success).toHaveBeenCalledWith('Job deleted')
    })
  })

  it('shows starred jobs before unstarred jobs', async () => {
    const unstarred = { ...mockJd, id: 'jd-1', starred: false, job_title: 'Unstarred Job' }
    const starred = { ...mockJd, id: 'jd-2', starred: true, job_title: 'Starred Job' }
    vi.mocked(api.jobApi.list).mockResolvedValue([unstarred, starred])
    renderPage()

    await waitFor(() => {
      const cards = screen.getAllByRole('heading', { level: 3 })
      expect(cards[0]).toHaveTextContent('Starred Job')
      expect(cards[1]).toHaveTextContent('Unstarred Job')
    })
  })

  it('shows sort dropdown with options', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    renderPage()

    await waitFor(() => screen.getByText('Senior Python Developer'))

    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    expect(screen.getByText('Newest saved')).toBeInTheDocument()
    expect(screen.getByText('A–Z by title')).toBeInTheDocument()
  })

  it('reverts starred state when update throws', async () => {
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd])
    vi.mocked(api.jobApi.update).mockRejectedValue(new Error('Network error'))
    renderPage()

    await waitFor(() => expect(screen.getByLabelText('Star job')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Star job'))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update')
    })
  })

  it('shows error toast when loading fails', async () => {
    vi.mocked(api.jobApi.list).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load jobs')
    })
  })

  it('filters by search text', async () => {
    const second = { ...mockJd, id: 'jd-2', list_name: null, job_title: 'Junior Developer', company_name: 'OtherCo' }
    vi.mocked(api.jobApi.list).mockResolvedValue([mockJd, second])
    renderPage()

    await waitFor(() => screen.getByText('Senior Python Developer'))

    fireEvent.change(screen.getByPlaceholderText('Search by company or job title…'), {
      target: { value: 'TechAB' },
    })

    expect(screen.getByText('Senior Python Developer')).toBeInTheDocument()
    expect(screen.queryByText('Junior Developer')).not.toBeInTheDocument()
  })
})
