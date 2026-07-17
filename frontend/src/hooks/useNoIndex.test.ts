import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useNoIndex } from './useNoIndex'

function getRobotsMeta(): HTMLMetaElement | null {
  return document.head.querySelector('meta[name="robots"]')
}

describe('useNoIndex', () => {
  it('injects a noindex meta tag while mounted', () => {
    expect(getRobotsMeta()).toBeNull()

    const { unmount } = renderHook(() => useNoIndex())

    const meta = getRobotsMeta()
    expect(meta).not.toBeNull()
    expect(meta?.content).toBe('noindex')

    unmount()
  })

  it('removes the meta tag on unmount', () => {
    const { unmount } = renderHook(() => useNoIndex())
    expect(getRobotsMeta()).not.toBeNull()

    unmount()

    expect(getRobotsMeta()).toBeNull()
  })
})
