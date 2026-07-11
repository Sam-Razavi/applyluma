import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { scorePassword } from '../../lib/passwordStrength'
import { PasswordStrengthMeter } from './PasswordStrengthMeter'

describe('scorePassword', () => {
  it('returns score 0 for an empty password', () => {
    expect(scorePassword('')).toEqual({ score: 0, label: '', textColor: '' })
  })

  it('scores a minimal 8-char password as Weak', () => {
    expect(scorePassword('abcdefg1').label).toBe('Weak')
  })

  it('scores a long mixed password as Strong', () => {
    const result = scorePassword('CorrectHorse99!')
    expect(result.score).toBe(3)
    expect(result.label).toBe('Strong')
  })

  it('forces common passwords down to Weak regardless of heuristics', () => {
    expect(scorePassword('Password123').label).toBe('Weak')
    expect(scorePassword('Qwerty123').label).toBe('Weak')
  })
})

describe('PasswordStrengthMeter', () => {
  it('renders nothing when password is empty', () => {
    const { container } = render(<PasswordStrengthMeter password="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the strength label for a password', () => {
    render(<PasswordStrengthMeter password="CorrectHorse99!" />)
    expect(screen.getByText('Strength:')).toBeInTheDocument()
    expect(screen.getByText('Strong')).toBeInTheDocument()
  })
})
