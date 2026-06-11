import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { CookieBanner } from './CookieBanner'

describe('CookieBanner', () => {
  it('renders the banner when consent is null', () => {
    render(<CookieBanner consent={null} onAccept={vi.fn()} onDecline={vi.fn()} />)

    expect(screen.getByRole('button', { name: /accept all/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /decline optional/i })).toBeInTheDocument()
  })

  it('renders nothing when consent is accepted', () => {
    const { container } = render(
      <CookieBanner consent="accepted" onAccept={vi.fn()} onDecline={vi.fn()} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when consent is declined', () => {
    const { container } = render(
      <CookieBanner consent="declined" onAccept={vi.fn()} onDecline={vi.fn()} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('calls onAccept when Accept all is clicked', () => {
    const onAccept = vi.fn()
    render(<CookieBanner consent={null} onAccept={onAccept} onDecline={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /accept all/i }))

    expect(onAccept).toHaveBeenCalledTimes(1)
  })

  it('calls onDecline when Decline optional is clicked', () => {
    const onDecline = vi.fn()
    render(<CookieBanner consent={null} onAccept={vi.fn()} onDecline={onDecline} />)

    fireEvent.click(screen.getByRole('button', { name: /decline optional/i }))

    expect(onDecline).toHaveBeenCalledTimes(1)
  })
})
