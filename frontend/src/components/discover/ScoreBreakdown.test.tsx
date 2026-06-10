import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ScoreBreakdown from './ScoreBreakdown'

const fullProps = {
  skillsMatch: 85,
  experienceMatch: 70,
  salaryMatchScore: 90,
  educationMatch: 55,
  locationMatch: 80,
  explanation: 'Strong skills match.',
}

describe('ScoreBreakdown', () => {
  it('renders the "Score breakdown" heading', () => {
    render(<ScoreBreakdown {...fullProps} />)
    expect(screen.getByText('Score breakdown')).toBeInTheDocument()
  })

  it('shows all score rows when open', () => {
    render(<ScoreBreakdown {...fullProps} />)
    expect(screen.getByText(/Skills/)).toBeInTheDocument()
    expect(screen.getByText(/Experience/)).toBeInTheDocument()
    expect(screen.getByText(/Salary/)).toBeInTheDocument()
    expect(screen.getByText(/Education/)).toBeInTheDocument()
    expect(screen.getByText(/Location/)).toBeInTheDocument()
  })

  it('shows score band labels for each row', () => {
    render(<ScoreBreakdown {...fullProps} />)
    // skillsMatch=85 → Strong, salaryMatchScore=90 → Strong
    expect(screen.getAllByText(/Strong/).length).toBeGreaterThan(0)
    // experienceMatch=70 → Partial, locationMatch=80 is exactly 80 → Strong
    expect(screen.getAllByText(/Partial/).length).toBeGreaterThan(0)
    // educationMatch=55 → Gap
    expect(screen.getAllByText(/Gap/).length).toBeGreaterThan(0)
  })

  it('shows explanation text', () => {
    render(<ScoreBreakdown {...fullProps} />)
    expect(screen.getByText('Strong skills match.')).toBeInTheDocument()
  })

  it('hides rows when toggle button is clicked', () => {
    render(<ScoreBreakdown {...fullProps} />)
    const toggle = screen.getByRole('button')
    fireEvent.click(toggle)
    expect(screen.queryByText(/Skills/)).not.toBeInTheDocument()
  })

  it('re-opens after two clicks', () => {
    render(<ScoreBreakdown {...fullProps} />)
    const toggle = screen.getByRole('button')
    fireEvent.click(toggle)
    fireEvent.click(toggle)
    expect(screen.getByText(/Skills/)).toBeInTheDocument()
  })

  it('shows unavailable message when all scores are null', () => {
    render(
      <ScoreBreakdown
        skillsMatch={null}
        experienceMatch={null}
        salaryMatchScore={null}
        educationMatch={null}
        locationMatch={null}
        explanation={null}
      />,
    )
    expect(screen.getByText(/Score details unavailable/)).toBeInTheDocument()
  })

  it('skips null score rows but renders non-null ones', () => {
    render(
      <ScoreBreakdown
        skillsMatch={90}
        experienceMatch={null}
        salaryMatchScore={null}
        educationMatch={null}
        locationMatch={null}
        explanation={null}
      />,
    )
    expect(screen.getByText(/Skills/)).toBeInTheDocument()
    expect(screen.queryByText(/Experience/)).not.toBeInTheDocument()
  })

  it('does not render explanation when explanation is null', () => {
    render(<ScoreBreakdown {...fullProps} explanation={null} />)
    expect(screen.queryByText('Strong skills match.')).not.toBeInTheDocument()
  })

  it('renders weight percentage for each row', () => {
    render(<ScoreBreakdown {...fullProps} />)
    expect(screen.getByText('(40%)')).toBeInTheDocument()
    expect(screen.getByText('(30%)')).toBeInTheDocument()
  })
})
