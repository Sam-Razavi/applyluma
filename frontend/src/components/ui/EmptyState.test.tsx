import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import EmptyState from './EmptyState'

describe('EmptyState', () => {
  it('renders a default title', () => {
    render(<EmptyState />)
    expect(screen.getByText('Nothing to show here yet')).toBeInTheDocument()
  })

  it('renders a custom title and description', () => {
    render(<EmptyState title="No CVs yet" description="Upload your first CV above to get started." />)
    expect(screen.getByText('No CVs yet')).toBeInTheDocument()
    expect(screen.getByText('Upload your first CV above to get started.')).toBeInTheDocument()
  })

  it('does not render an action button by default', () => {
    render(<EmptyState />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('calls the action onClick when clicked', () => {
    const onClick = vi.fn()
    render(<EmptyState action={{ label: 'Add a job', onClick }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Add a job' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
