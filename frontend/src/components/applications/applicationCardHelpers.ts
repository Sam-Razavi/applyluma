export const BADGE_ACTIVE = 'bg-chip-accent text-accent-text border border-accent-muted'
export const BADGE_SUCCESS = 'bg-chip-success text-chip-success-fg border border-chip-success'
export const BADGE_ERROR = 'bg-chip-danger text-chip-danger-fg border border-chip-danger'
export const BADGE_NEUTRAL = 'bg-surface text-fg-muted border border-line'

export const priorityClasses: Record<number, string> = {
  1: BADGE_NEUTRAL,
  2: BADGE_ACTIVE,
  3: BADGE_ERROR,
}

export const priorityLabels: Record<number, string> = {
  1: 'Low',
  2: 'Med',
  3: 'High',
}

/** Today's date as YYYY-MM-DD in the user's *local* time (toISOString would be UTC). */
export function todayISO(): string {
  // sv-SE locale formats as YYYY-MM-DD
  return new Date().toLocaleDateString('sv-SE')
}

/**
 * applied_date is a calendar date picked in a date input and stored as
 * midnight UTC. Read its date part as a local date: converting the instant to
 * local time shows the previous day for anyone west of UTC.
 */
function calendarDate(value: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return new Date(value)
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

export function formatDate(value: string | null): string {
  if (!value) return 'Not applied'
  return calendarDate(value).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  // Whole calendar days; round absorbs a DST hour.
  return Math.round((startOfToday.getTime() - calendarDate(dateStr).getTime()) / 86_400_000)
}

export function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000)
}

export const FOLLOWUP_STATUSES = new Set(['applied', 'phone_screen'])
export const TERMINAL_STATUSES = new Set(['rejected', 'withdrawn', 'offer'])
