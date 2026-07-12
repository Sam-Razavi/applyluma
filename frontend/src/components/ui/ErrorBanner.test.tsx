import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBanner from './ErrorBanner'

describe('ErrorBanner', () => {
  it('renders the message text', () => {
    render(<ErrorBanner message="Failed to load database stats" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Failed to load database stats')
  })
})
