import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as applicationsApi from './applicationsApi'
import client from '../api/client'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockApp = {
  id: 'app-1',
  user_id: 'user-1',
  company: 'Acme',
  position: 'Engineer',
  status: 'applied',
  events: [{ id: 'ev-1' }],
  contacts: [{ id: 'ct-1' }],
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
}

describe('applicationsApi', () => {
  beforeEach(() => vi.clearAllMocks())

  describe('fetchApplications', () => {
    it('returns applications with events and contacts intact', async () => {
      vi.mocked(client.get).mockResolvedValue({ data: [mockApp] })
      const result = await applicationsApi.fetchApplications()
      expect(result[0].events).toEqual([{ id: 'ev-1' }])
      expect(result[0].contacts).toEqual([{ id: 'ct-1' }])
    })

    it('normalizes null events and contacts to empty arrays', async () => {
      vi.mocked(client.get).mockResolvedValue({
        data: [{ ...mockApp, events: null, contacts: null }],
      })
      const result = await applicationsApi.fetchApplications()
      expect(result[0].events).toEqual([])
      expect(result[0].contacts).toEqual([])
    })

    it('passes status filter as query param', async () => {
      vi.mocked(client.get).mockResolvedValue({ data: [] })
      await applicationsApi.fetchApplications('applied')
      expect(client.get).toHaveBeenCalledWith('/api/v1/applications', {
        params: { status: 'applied' },
      })
    })

    it('omits params when no status filter given', async () => {
      vi.mocked(client.get).mockResolvedValue({ data: [] })
      await applicationsApi.fetchApplications()
      expect(client.get).toHaveBeenCalledWith('/api/v1/applications', {
        params: undefined,
      })
    })
  })

  describe('createApplication', () => {
    it('POSTs and returns normalized application', async () => {
      vi.mocked(client.post).mockResolvedValue({
        data: { ...mockApp, events: null, contacts: null },
      })
      const result = await applicationsApi.createApplication({
        company: 'Acme',
        position: 'Engineer',
        status: 'applied',
      } as any)
      expect(client.post).toHaveBeenCalledWith('/api/v1/applications', expect.any(Object))
      expect(result.events).toEqual([])
      expect(result.contacts).toEqual([])
    })
  })

  describe('updateApplication', () => {
    it('PATCHes correct URL and returns normalized application', async () => {
      vi.mocked(client.patch).mockResolvedValue({ data: mockApp })
      const result = await applicationsApi.updateApplication('app-1', { status: 'interview' } as any)
      expect(client.patch).toHaveBeenCalledWith('/api/v1/applications/app-1', { status: 'interview' })
      expect(result.id).toBe('app-1')
    })
  })

  describe('deleteApplication', () => {
    it('DELETEs correct URL and returns undefined', async () => {
      vi.mocked(client.delete).mockResolvedValue({})
      const result = await applicationsApi.deleteApplication('app-1')
      expect(client.delete).toHaveBeenCalledWith('/api/v1/applications/app-1')
      expect(result).toBeUndefined()
    })
  })

  describe('fetchStats', () => {
    it('returns stats data', async () => {
      const stats = { total: 10, applied: 5, interview: 2 }
      vi.mocked(client.get).mockResolvedValue({ data: stats })
      const result = await applicationsApi.fetchStats()
      expect(result).toEqual(stats)
      expect(client.get).toHaveBeenCalledWith('/api/v1/applications/stats')
    })
  })

  describe('fetchApplicationAnalytics', () => {
    it('returns analytics data', async () => {
      const analytics = { by_status: [], weekly: [] }
      vi.mocked(client.get).mockResolvedValue({ data: analytics })
      const result = await applicationsApi.fetchApplicationAnalytics()
      expect(result).toEqual(analytics)
      expect(client.get).toHaveBeenCalledWith('/api/v1/applications/analytics')
    })
  })

  describe('addApplicationContact', () => {
    it('POSTs to correct URL and returns contact', async () => {
      const contact = { id: 'c-1', name: 'Jane' }
      vi.mocked(client.post).mockResolvedValue({ data: contact })
      const result = await applicationsApi.addApplicationContact('app-1', { name: 'Jane' } as any)
      expect(client.post).toHaveBeenCalledWith('/api/v1/applications/app-1/contacts', { name: 'Jane' })
      expect(result).toEqual(contact)
    })
  })

  describe('deleteApplicationContact', () => {
    it('DELETEs correct URL and returns undefined', async () => {
      vi.mocked(client.delete).mockResolvedValue({})
      const result = await applicationsApi.deleteApplicationContact('app-1', 'c-1')
      expect(client.delete).toHaveBeenCalledWith('/api/v1/applications/app-1/contacts/c-1')
      expect(result).toBeUndefined()
    })
  })
})
