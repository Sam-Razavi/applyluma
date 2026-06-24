import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

// Suppress React's error boundary console output in tests
beforeAll(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterAll(() => {
  vi.mocked(console.error).mockRestore()
})

function Bomb(): JSX.Element {
  throw new Error('Test explosion')
}

describe('ErrorBoundary', () => {
  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Child content')).toBeInTheDocument()
  })

  it('shows fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('resets error state when Try again is clicked', () => {
    let shouldThrow = true

    function Conditional() {
      if (shouldThrow) throw new Error('Test error')
      return <div>Recovered content</div>
    }

    render(
      <ErrorBoundary>
        <Conditional />
      </ErrorBoundary>
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    shouldThrow = false
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(screen.getByText('Recovered content')).toBeInTheDocument()
  })

  it('renders a custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error UI</div>}>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText('Custom error UI')).toBeInTheDocument()
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
  })
})

function ChunkBomb(): JSX.Element {
  throw new Error('Failed to fetch dynamically imported module: https://x/assets/Page-abc.js')
}

describe('ErrorBoundary chunk-load recovery', () => {
  const realLocation = window.location
  const reloadMock = vi.fn()

  beforeAll(() => {
    // @ts-expect-error jsdom location is read-only; replace it for the test
    delete window.location
    // @ts-expect-error provide a writable stand-in with a mocked reload
    window.location = { ...realLocation, reload: reloadMock }
  })

  afterAll(() => {
    // @ts-expect-error restore the original location
    window.location = realLocation
  })

  beforeEach(() => {
    reloadMock.mockClear()
    sessionStorage.clear()
  })

  it('reloads once when a chunk-load error is thrown', () => {
    render(
      <ErrorBoundary>
        <ChunkBomb />
      </ErrorBoundary>
    )
    expect(reloadMock).toHaveBeenCalledTimes(1)
  })

  it('does not reload again if a reload was already attempted this session', () => {
    sessionStorage.setItem('chunk-reload-attempted', '1')
    render(
      <ErrorBoundary>
        <ChunkBomb />
      </ErrorBoundary>
    )
    expect(reloadMock).not.toHaveBeenCalled()
    // Falls back to the normal error UI instead of looping reloads.
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('does not reload for ordinary (non-chunk) errors', () => {
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(reloadMock).not.toHaveBeenCalled()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })
})
