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

export function formatDate(value: string | null): string {
  if (!value) return 'Not applied'
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000)
}

export function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000)
}

export const FOLLOWUP_STATUSES = new Set(['applied', 'phone_screen'])
export const TERMINAL_STATUSES = new Set(['rejected', 'withdrawn', 'offer'])
