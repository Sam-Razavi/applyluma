import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Forbidden from './Forbidden'
import { useAuthStore } from '../stores'

function renderForbidden() {
  return render(
    <MemoryRouter>
      <Forbidden />
    </MemoryRouter>,
  )
}

describe('Forbidden', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('renders the heading and body copy', () => {
    renderForbidden()
    expect(screen.getByRole('heading', { name: /isn't available to you/i })).toBeInTheDocument()
    expect(screen.getByText(/don't have permission/i)).toBeInTheDocument()
  })

  it('shows a "Go home" link when logged out', () => {
    renderForbidden()
    const link = screen.getByRole('link', { name: /go home/i })
    expect(link).toHaveAttribute('href', '/')
  })

  it('shows a "Go to dashboard" link when logged in', () => {
    useAuthStore.setState({ token: 'test-token' })
    renderForbidden()
    const link = screen.getByRole('link', { name: /go to dashboard/i })
    expect(link).toHaveAttribute('href', '/dashboard')
  })
})
