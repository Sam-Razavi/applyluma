import type { HiringPatternPoint } from '../types'

const DAY_MS = 86_400_000

export interface WeeklyPostings {
  thisWeek: number
  /** Change against the 7 days before, in percent. null when that week has
   *  no ads: growth from zero is not a number worth showing. */
  growthPct: number | null
}

/** New job ads in the last 7 days, from the daily hiring-patterns series. */
export function weeklyPostings(points: HiringPatternPoint[], today: Date = new Date()): WeeklyPostings {
  const start = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  let thisWeek = 0
  let lastWeek = 0
  for (const point of points) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(point.period)) continue
    const age = Math.round((start - Date.parse(`${point.period}T00:00:00Z`)) / DAY_MS)
    if (age >= 0 && age < 7) thisWeek += point.job_count
    else if (age >= 7 && age < 14) lastWeek += point.job_count
  }
  const growthPct = lastWeek === 0 ? null : Math.round(((thisWeek - lastWeek) / lastWeek) * 1000) / 10
  return { thisWeek, growthPct }
}
