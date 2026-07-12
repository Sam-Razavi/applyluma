import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ErrorState from './ErrorState'

describe('ErrorState', () => {
  it('renders the description and a default title', () => {
    render(<ErrorState description="Could not load your data." />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('Could not load your data.')).toBeInTheDocument()
  })

  it('renders a custom title when provided', () => {
    render(<ErrorState title="Failed to load data" description="Network error" />)
    expect(screen.getByText('Failed to load data')).toBeInTheDocument()
  })

  it('does not render a retry button when onRetry is omitted', () => {
    render(<ErrorState description="Network error" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('calls onRetry when the retry button is clicked', () => {
    const onRetry = vi.fn()
    render(<ErrorState description="Network error" onRetry={onRetry} />)
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders a solid CTA button for the full size variant', () => {
    const onRetry = vi.fn()
    render(<ErrorState size="full" description="Network error" onRetry={onRetry} />)
    const button = screen.getByRole('button', { name: /try again/i })
    expect(button.className).toContain('bg-primary-600')
  })
})
