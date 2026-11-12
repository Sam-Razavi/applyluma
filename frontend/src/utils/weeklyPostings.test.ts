import { describe, expect, it } from 'vitest'
import { weeklyPostings } from './weeklyPostings'
import type { HiringPatternPoint } from '../types'

const point = (period: string, job_count: number): HiringPatternPoint => ({
  period,
  job_count,
  remote_count: 0,
  remote_percentage: 0,
  avg_salary: null,
})

const TODAY = new Date('2026-11-11T09:00:00Z')

describe('weeklyPostings', () => {
  it('sums the last 7 days and compares them with the 7 before', () => {
    const result = weeklyPostings(
      [
        point('2026-11-11', 40), // today
        point('2026-11-05', 80), // 6 days ago: still this week
        point('2026-11-04', 60), // 7 days ago: last week
        point('2026-10-29', 40), // 13 days ago: last week
        point('2026-10-28', 500), // 14 days ago: outside both
      ],
      TODAY,
    )

    expect(result).toEqual({ thisWeek: 120, growthPct: 20 })
  })

  it('reports a fall as a negative percentage', () => {
    const result = weeklyPostings([point('2026-11-10', 50), point('2026-11-03', 200)], TODAY)

    expect(result).toEqual({ thisWeek: 50, growthPct: -75 })
  })

  it('gives no growth figure when the earlier week is empty', () => {
    expect(weeklyPostings([point('2026-11-10', 50)], TODAY)).toEqual({ thisWeek: 50, growthPct: null })
    expect(weeklyPostings([], TODAY)).toEqual({ thisWeek: 0, growthPct: null })
  })

  it('ignores weekly and monthly periods', () => {
    expect(weeklyPostings([point('2026-W45', 99), point('2026-11', 99)], TODAY)).toEqual({
      thisWeek: 0,
      growthPct: null,
    })
  })
})
