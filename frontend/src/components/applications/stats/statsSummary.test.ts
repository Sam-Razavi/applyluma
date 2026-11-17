import { describe, expect, it } from 'vitest'
import { buildSummary, pct, weeklyChangePct } from './statsSummary'
import type { ApplicationInsights } from '../../../types/application'

function insights(overrides: Partial<ApplicationInsights> = {}): ApplicationInsights {
  return {
    total: 10,
    submitted: 8,
    active: 6,
    closed: 2,
    wishlist: 2,
    applied_last_7d: 3,
    applied_prev_7d: 2,
    applied_last_30d: 7,
    interview_rate: 0.25,
    awaiting_reply: 2,
    awaiting_reply_days: 14,
    daily_counts: [],
    stage_reach: [],
    work_modes: [],
    top_locations: [],
    top_companies: [],
    weekday_counts: [],
    source_performance: [],
    cv_performance: [],
    upcoming: [],
    salary_median: null,
    salary_min: null,
    salary_max: null,
    salary_sample: 0,
    ...overrides,
  }
}

describe('statsSummary', () => {
  it('formats rates as whole percents', () => {
    expect(pct(0.256)).toBe('26%')
  })

  it('computes the week-on-week change, or null with no baseline', () => {
    expect(weeklyChangePct(insights())).toBe(50)
    expect(weeklyChangePct(insights({ applied_prev_7d: 0 }))).toBeNull()
  })

  it('describes volume, replies and waiting applications', () => {
    const lines = buildSummary({ response_rate: 0.5, average_response_days: 4.2 }, insights())
    expect(lines).toEqual([
      'You have sent 8 applications so far, 3 of them in the last 7 days.',
      '50% have had a reply and 25% reached an interview; replies take about 4.2 days.',
      '2 applications have had no reply for 14+ days. A short follow-up is worth sending.',
    ])
  })

  it('handles singular wording, no recent activity and no reply time', () => {
    const lines = buildSummary(
      { response_rate: 0, average_response_days: null },
      insights({ submitted: 1, applied_last_7d: 0, awaiting_reply: 1, interview_rate: 0 }),
    )
    expect(lines[0]).toBe('You have sent 1 application so far, none in the last 7 days.')
    expect(lines[1]).toBe('0% have had a reply and 0% reached an interview.')
    expect(lines[2]).toContain('1 application has had no reply')
  })

  it('points wishlist-only users to the next step', () => {
    const lines = buildSummary(
      { response_rate: 0, average_response_days: null },
      insights({ submitted: 0, wishlist: 1 }),
    )
    expect(lines).toHaveLength(1)
    expect(lines[0]).toContain('1 job on your wishlist')
  })
})
