import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useApplicationsStore } from './applications'
import * as api from '../services/applicationsApi'
import type { Application } from '../types/application'

vi.mock('../services/applicationsApi', () => ({
  fetchApplications: vi.fn(),
  fetchStats: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  deleteApplication: vi.fn(),
  addApplicationContact: vi.fn(),
  deleteApplicationContact: vi.fn(),
}))

function app(id: string, status: Application['status']): Application {
  return { id, status, company_name: 'Acme', job_title: 'Dev', events: [], contacts: [] } as unknown as Application
}

const all = [app('a', 'applied'), app('b', 'rejected'), app('c', 'interview')]

describe('applications store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useApplicationsStore.setState({
      applications: [],
      filters: { status: '', search: '' },
    })
    // Behave like the real endpoint: a status argument filters server-side.
    vi.mocked(api.fetchApplications).mockImplementation(async (status) =>
      status ? all.filter((a) => a.status === status) : all,
    )
    vi.mocked(api.fetchStats).mockResolvedValue({
      wishlist: 0,
      applied: 1,
      phone_screen: 0,
      interview: 1,
      offer: 0,
      rejected: 1,
      withdrawn: 0,
    })
  })

  it('loads every application even when a status filter is set', async () => {
    useApplicationsStore.getState().setFilters({ status: 'rejected' })
    await useApplicationsStore.getState().fetchApplications()

    expect(api.fetchApplications).toHaveBeenCalledWith()
    expect(useApplicationsStore.getState().applications).toHaveLength(3)
  })

  it('keeps other statuses in stats after an update with a status filter set', async () => {
    useApplicationsStore.getState().setFilters({ status: 'rejected' })
    await useApplicationsStore.getState().fetchApplications()
    vi.mocked(api.updateApplication).mockResolvedValue(app('b', 'withdrawn'))

    await useApplicationsStore.getState().updateApplication('b', { status: 'withdrawn' })

    const { stats } = useApplicationsStore.getState()
    expect(stats.applied).toBe(1)
    expect(stats.interview).toBe(1)
    expect(stats.withdrawn).toBe(1)
    expect(stats.rejected).toBe(0)
  })
})
