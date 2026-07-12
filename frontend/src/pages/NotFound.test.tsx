import { describe, it, expect, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotFound from './NotFound'
import { useAuthStore } from '../stores'

function renderNotFound() {
  return render(
    <MemoryRouter>
      <NotFound />
    </MemoryRouter>,
  )
}

describe('NotFound', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('shows a "Go home" link when logged out', () => {
    renderNotFound()
    const link = screen.getByRole('link', { name: /go home/i })
    expect(link).toHaveAttribute('href', '/')
  })

  it('shows a "Go to dashboard" link when logged in', () => {
    useAuthStore.setState({ token: 'test-token' })
    renderNotFound()
    const link = screen.getByRole('link', { name: /go to dashboard/i })
    expect(link).toHaveAttribute('href', '/dashboard')
  })

  it('renders the heading', () => {
    renderNotFound()
    expect(screen.getByRole('heading', { name: /couldn't find that page/i })).toBeInTheDocument()
  })

  it('calls window.history.back when "Go back" is clicked', () => {
    const backSpy = vi.spyOn(window.history, 'back').mockImplementation(() => undefined)
    renderNotFound()
    fireEvent.click(screen.getByRole('button', { name: /go back/i }))
    expect(backSpy).toHaveBeenCalledTimes(1)
    backSpy.mockRestore()
  })
})
