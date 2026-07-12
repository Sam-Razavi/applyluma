import { describe, it, expect, afterEach } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { OfflineBanner } from './OfflineBanner'

function setNavigatorOnLine(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value })
}

describe('OfflineBanner', () => {
  afterEach(() => {
    setNavigatorOnLine(true)
  })

  it('renders nothing while online', () => {
    setNavigatorOnLine(true)
    render(<OfflineBanner />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows the offline message when offline', () => {
    setNavigatorOnLine(false)
    render(<OfflineBanner />)
    expect(screen.getByRole('status')).toHaveTextContent(/you're offline/i)
  })

  it('hides again once the online event fires', async () => {
    setNavigatorOnLine(false)
    render(<OfflineBanner />)
    expect(screen.getByRole('status')).toBeInTheDocument()

    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument())
  })
})
