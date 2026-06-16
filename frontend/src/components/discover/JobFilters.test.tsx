import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import JobFilters from './JobFilters'
import type { JobFilters as JobFiltersType } from '../../types/jobDiscovery'

const defaultFilters: JobFiltersType = {
  search: '',
  location: '',
  salary_min: '',
  salary_max: '',
  keywords: '',
  source: '',
  remote_only: false,
  match_score_min: '',
  sort: 'score_desc',
}

describe('JobFilters', () => {
  it('renders the sort select with default value', () => {
    render(<JobFilters filters={defaultFilters} onChange={vi.fn()} onReset={vi.fn()} />)
    expect(screen.getByDisplayValue('Best match')).toBeInTheDocument()
  })

  it('does not render Reset button when no filters are active', () => {
    render(<JobFilters filters={defaultFilters} onChange={vi.fn()} onReset={vi.fn()} />)
    expect(screen.queryByText('Reset')).not.toBeInTheDocument()
  })

  it('renders Reset button when location filter is active', () => {
    render(
      <JobFilters
        filters={{ ...defaultFilters, location: 'Stockholm' }}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('renders Reset button when keywords filter is active', () => {
    render(
      <JobFilters
        filters={{ ...defaultFilters, keywords: 'Python' }}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('renders Reset button when source filter is active', () => {
    render(
      <JobFilters
        filters={{ ...defaultFilters, source: 'Platsbanken' }}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('renders Reset button when remote-only filter is active', () => {
    render(
      <JobFilters
        filters={{ ...defaultFilters, remote_only: true }}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )
    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('calls onReset when Reset is clicked', () => {
    const onReset = vi.fn()
    render(
      <JobFilters
        filters={{ ...defaultFilters, keywords: 'Python' }}
        onChange={vi.fn()}
        onReset={onReset}
      />,
    )
    fireEvent.click(screen.getByText('Reset'))
    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('calls onChange with updated location when input changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('e.g. Stockholm'), {
      target: { value: 'Gothenburg' },
    })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, location: 'Gothenburg' })
  })

  it('calls onChange with updated keywords when input changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Python, React, Docker…'), {
      target: { value: 'React' },
    })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, keywords: 'React' })
  })

  it('calls onChange with updated sort when select changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByDisplayValue('Best match'), {
      target: { value: 'date_posted' },
    })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, sort: 'date_posted' })
  })

  it('calls onChange with updated source when source select changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[1], { target: { value: 'the_muse' } })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, source: 'the_muse' })
  })

  it('calls onChange when remote-only checkbox changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.click(screen.getByLabelText('Remote only'))
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, remote_only: true })
  })

  it('calls onChange when salary_min input changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Min'), { target: { value: '30000' } })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, salary_min: '30000' })
  })

  it('calls onChange when salary_max input changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Max'), { target: { value: '60000' } })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, salary_max: '60000' })
  })

  it('calls onChange when match_score_min input changes', () => {
    const onChange = vi.fn()
    render(<JobFilters filters={defaultFilters} onChange={onChange} onReset={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('e.g. 70'), { target: { value: '70' } })
    expect(onChange).toHaveBeenCalledWith({ ...defaultFilters, match_score_min: '70' })
  })

  it('toggles mobile panel aria-expanded when header button clicked', () => {
    render(<JobFilters filters={defaultFilters} onChange={vi.fn()} onReset={vi.fn()} />)
    const toggleBtn = screen.getByRole('button', { name: /filters/i })
    expect(toggleBtn).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveAttribute('aria-expanded', 'true')
  })

  it('shows "On" active filters badge when filters are active', () => {
    render(
      <JobFilters
        filters={{ ...defaultFilters, match_score_min: '70' }}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    )
    expect(screen.getByText('On')).toBeInTheDocument()
  })
})
