export const MATCH_WEIGHTS = {
  skills_match: 40,
  experience_match: 30,
  salary_match_score: 15,
  education_match: 10,
  location_match: 5,
} as const

export function scoreBand(value: number | null): string {
  if (value === null) return 'Not scored'
  if (value >= 80) return 'Strong'
  if (value >= 60) return 'Partial'
  return 'Gap'
}
