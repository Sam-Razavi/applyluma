import { describe, it, expect } from 'vitest'
import { MATCH_WEIGHTS, scoreBand } from './matchScore'

describe('MATCH_WEIGHTS', () => {
  it('has the correct weight for each factor', () => {
    expect(MATCH_WEIGHTS.skills_match).toBe(40)
    expect(MATCH_WEIGHTS.experience_match).toBe(30)
    expect(MATCH_WEIGHTS.salary_match_score).toBe(15)
    expect(MATCH_WEIGHTS.education_match).toBe(10)
    expect(MATCH_WEIGHTS.location_match).toBe(5)
  })
})

describe('scoreBand', () => {
  it('returns "Not scored" for null', () => {
    expect(scoreBand(null)).toBe('Not scored')
  })

  it('returns "Strong" for value >= 80', () => {
    expect(scoreBand(80)).toBe('Strong')
    expect(scoreBand(95)).toBe('Strong')
    expect(scoreBand(100)).toBe('Strong')
  })

  it('returns "Partial" for value in [60, 79]', () => {
    expect(scoreBand(60)).toBe('Partial')
    expect(scoreBand(79)).toBe('Partial')
  })

  it('returns "Gap" for value < 60', () => {
    expect(scoreBand(59)).toBe('Gap')
    expect(scoreBand(0)).toBe('Gap')
  })
})
