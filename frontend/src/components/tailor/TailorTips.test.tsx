import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { TailorTips } from './TailorTips'
import { CV_TIPS } from '../../lib/cvTips'

describe('TailorTips', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders one tip from CV_TIPS on mount', () => {
    render(<TailorTips />)

    const shown = screen.getByText((text) => CV_TIPS.includes(text))
    expect(shown).toBeInTheDocument()
  })

  it('rotates to a different tip after the interval without repeating', async () => {
    render(<TailorTips />)

    const first = screen.getByText((text) => CV_TIPS.includes(text)).textContent

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5500)
    })
    const second = screen.getByText((text) => CV_TIPS.includes(text)).textContent
    expect(second).not.toBe(first)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5500)
    })
    const third = screen.getByText((text) => CV_TIPS.includes(text)).textContent
    expect(third).not.toBe(second)
  })

  it('stops rotating once unmounted', async () => {
    const { unmount } = render(<TailorTips />)
    unmount()

    await expect(vi.advanceTimersByTimeAsync(20000)).resolves.not.toThrow()
  })
})
