import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SkillsBreakdown from './SkillsBreakdown'

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

describe('SkillsBreakdown', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows upload prompt when no skills provided', () => {
    render(<SkillsBreakdown matchedSkills={[]} missingSkills={[]} />)
    expect(screen.getByText(/Upload a CV/)).toBeInTheDocument()
    expect(screen.getByText('Skills match')).toBeInTheDocument()
  })

  it('shows matched and missing skill counts', () => {
    render(<SkillsBreakdown matchedSkills={['Python', 'React']} missingSkills={['Docker']} />)
    expect(screen.getByText(/2 of 3 required skills matched/)).toBeInTheDocument()
  })

  it('renders matched skill pills', () => {
    render(<SkillsBreakdown matchedSkills={['Python', 'React']} missingSkills={[]} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
  })

  it('renders missing skill pills', () => {
    render(<SkillsBreakdown matchedSkills={[]} missingSkills={['Docker', 'Kubernetes']} />)
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
  })

  it('shows "None yet" when matchedSkills is empty but missingSkills exist', () => {
    render(<SkillsBreakdown matchedSkills={[]} missingSkills={['Docker']} />)
    expect(screen.getByText('None yet')).toBeInTheDocument()
  })

  it('shows "No gaps found" when missingSkills is empty but matchedSkills exist', () => {
    render(<SkillsBreakdown matchedSkills={['Python']} missingSkills={[]} />)
    expect(screen.getByText('No gaps found')).toBeInTheDocument()
  })

  it('copies skill to clipboard when missing skill pill is clicked', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    render(<SkillsBreakdown matchedSkills={[]} missingSkills={['Docker']} />)
    fireEvent.click(screen.getByText('Docker'))

    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('Docker')
    })
  })

  it('calls onSkillClick when a matched skill pill is clicked', () => {
    const onSkillClick = vi.fn()
    render(
      <SkillsBreakdown matchedSkills={['Python']} missingSkills={[]} onSkillClick={onSkillClick} />,
    )
    fireEvent.click(screen.getByText('Python'))
    expect(onSkillClick).toHaveBeenCalledWith('Python')
  })

  it('calls onSkillClick instead of copying when a missing skill pill is clicked', () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    const onSkillClick = vi.fn()

    render(
      <SkillsBreakdown matchedSkills={[]} missingSkills={['Docker']} onSkillClick={onSkillClick} />,
    )
    fireEvent.click(screen.getByText('Docker'))

    expect(onSkillClick).toHaveBeenCalledWith('Docker')
    expect(writeText).not.toHaveBeenCalled()
  })
})
