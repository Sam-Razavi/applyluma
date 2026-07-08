import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CompletenessBar, CompletenessChecklist } from './CvCompleteness'

const { mockCompleteness } = vi.hoisted(() => ({ mockCompleteness: vi.fn() }))

vi.mock('../../services/api', () => ({
  cvApi: { completeness: mockCompleteness },
}))

describe('CompletenessBar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the score percentage', () => {
    render(<CompletenessBar score={71} />)
    expect(screen.getByText('71%')).toBeInTheDocument()
    expect(screen.getByLabelText('CV completeness 71%')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<CompletenessBar score={40} onClick={onClick} />)
    fireEvent.click(screen.getByLabelText('CV completeness 40%'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})

describe('CompletenessChecklist', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders passed and failed checks with hints for failures', async () => {
    mockCompleteness.mockResolvedValue({
      score: 57,
      checks: [
        { id: 'contact_info', label: 'Contact information', passed: true, hint: 'Add an email.' },
        { id: 'links', label: 'Links', passed: false, hint: 'Include a LinkedIn link.' },
      ],
    })

    render(<CompletenessChecklist cvId="cv-1" />)

    expect(await screen.findByText('Contact information')).toBeInTheDocument()
    expect(screen.getByText('Links')).toBeInTheDocument()
    expect(screen.getByText('Include a LinkedIn link.')).toBeInTheDocument()
    // hints only shown for failed checks
    expect(screen.queryByText('Add an email.')).not.toBeInTheDocument()
    expect(mockCompleteness).toHaveBeenCalledWith('cv-1')
  })

  it('shows an error message when the fetch fails', async () => {
    mockCompleteness.mockRejectedValue(new Error('boom'))
    render(<CompletenessChecklist cvId="cv-1" />)
    expect(
      await screen.findByText('Could not load the completeness checklist.'),
    ).toBeInTheDocument()
  })
})
