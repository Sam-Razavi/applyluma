import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useUsageStore, atLimit, usageHint } from './usage'
import { tailorApi } from '../services/tailorApi'
import { coverLetterApi } from '../services/coverLetterApi'

vi.mock('../services/tailorApi', () => ({
  tailorApi: { getUsage: vi.fn() },
}))
vi.mock('../services/coverLetterApi', () => ({
  coverLetterApi: { getUsage: vi.fn() },
}))

const mockGetTailorUsage = vi.mocked(tailorApi.getUsage)
const mockGetCoverUsage = vi.mocked(coverLetterApi.getUsage)

const tailor = (used: number, limit: number | null) => ({
  used_today: used,
  daily_limit: limit,
  resets_at: '2026-06-24T00:00:00Z',
})

describe('atLimit', () => {
  it('is false for null usage or null daily_limit (unlimited)', () => {
    expect(atLimit(null)).toBe(false)
    expect(atLimit(tailor(99, null))).toBe(false)
  })

  it('is true only when a finite cap is reached', () => {
    expect(atLimit(tailor(0, 1))).toBe(false)
    expect(atLimit(tailor(1, 1))).toBe(true)
    expect(atLimit(tailor(2, 1))).toBe(true)
  })
})

describe('usageHint', () => {
  it('returns null when nothing is capped', () => {
    expect(usageHint(tailor(0, 1), tailor(0, 2))).toBeNull()
  })

  it('reports the still-available feature when one is capped', () => {
    expect(usageHint(tailor(1, 1), tailor(0, 2))).toMatch(/cover letter/i)
    expect(usageHint(tailor(0, 1), tailor(2, 2))).toMatch(/tailor your CV/i)
  })

  it('reports both when both are capped', () => {
    expect(usageHint(tailor(1, 1), tailor(2, 2))).toMatch(/Daily limits reached/i)
  })
})

describe('useUsageStore', () => {
  beforeEach(() => {
    useUsageStore.setState({ tailorUsage: null, coverUsage: null, loaded: false, loading: false })
    mockGetTailorUsage.mockReset()
    mockGetCoverUsage.mockReset()
  })

  it('loadUsage fetches both usages and caches them', async () => {
    mockGetTailorUsage.mockResolvedValue(tailor(1, 1))
    mockGetCoverUsage.mockResolvedValue(tailor(0, 2))

    await useUsageStore.getState().loadUsage()

    const state = useUsageStore.getState()
    expect(state.tailorUsage).toEqual(tailor(1, 1))
    expect(state.coverUsage).toEqual(tailor(0, 2))
    expect(state.loaded).toBe(true)
  })

  it('skips refetch once loaded unless forced', async () => {
    mockGetTailorUsage.mockResolvedValue(tailor(0, 1))
    mockGetCoverUsage.mockResolvedValue(tailor(0, 2))

    await useUsageStore.getState().loadUsage()
    await useUsageStore.getState().loadUsage()
    expect(mockGetTailorUsage).toHaveBeenCalledTimes(1)

    await useUsageStore.getState().loadUsage(true)
    expect(mockGetTailorUsage).toHaveBeenCalledTimes(2)
  })

  it('fails silently when the API errors', async () => {
    mockGetTailorUsage.mockRejectedValue(new Error('boom'))
    mockGetCoverUsage.mockResolvedValue(tailor(0, 2))

    await useUsageStore.getState().loadUsage()

    const state = useUsageStore.getState()
    expect(state.loaded).toBe(false)
    expect(state.loading).toBe(false)
  })
})
