import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { daysSince, formatDate, todayISO } from './applicationCardHelpers'

// applied_date comes back from the API as midnight UTC of the picked day.
const APPLIED = '2026-10-21T00:00:00Z'

describe.each(['America/Los_Angeles', 'Europe/Stockholm', 'UTC'])(
  'application dates in %s',
  (timeZone) => {
    let originalTz: string | undefined

    beforeEach(() => {
      originalTz = process.env.TZ
      process.env.TZ = timeZone
    })

    afterEach(() => {
      process.env.TZ = originalTz
      vi.useRealTimers()
    })

    it('shows the picked calendar day, not the previous one', () => {
      expect(formatDate(APPLIED)).toBe('Oct 21, 2026')
      expect(formatDate('2026-10-21T00:00:00+00:00')).toBe('Oct 21, 2026')
      expect(formatDate('2026-10-21')).toBe('Oct 21, 2026')
    })

    it('counts whole calendar days since the applied date', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date(2026, 9, 21, 9, 0)) // local 09:00 on the same day
      expect(daysSince(APPLIED)).toBe(0)
      vi.setSystemTime(new Date(2026, 9, 28, 23, 30))
      expect(daysSince(APPLIED)).toBe(7)
    })

    it("uses the local date for today's value", () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date(2026, 9, 21, 0, 30)) // just after local midnight
      expect(todayISO()).toBe('2026-10-21')
    })
  },
)

describe('formatDate', () => {
  it('labels a missing date', () => {
    expect(formatDate(null)).toBe('Not applied')
  })
})
