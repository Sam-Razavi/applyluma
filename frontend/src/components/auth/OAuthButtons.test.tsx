import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import OAuthButtons from './OAuthButtons'
import type { AuthProviders } from '../../services/authApi'

function providers(overrides: Partial<AuthProviders> = {}): AuthProviders {
  return { google: false, linkedin: false, github: false, magic_link: false, ...overrides }
}

describe('OAuthButtons', () => {
  it('renders a button per enabled provider', () => {
    render(<OAuthButtons providers={providers({ google: true, linkedin: true, github: true })} />)

    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue with linkedin/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue with github/i })).toBeInTheDocument()
  })

  it('renders only the enabled providers', () => {
    render(<OAuthButtons providers={providers({ linkedin: true })} />)

    expect(screen.getByRole('button', { name: /continue with linkedin/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /continue with google/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /continue with github/i })).not.toBeInTheDocument()
  })

  it('renders nothing when no OAuth provider is enabled', () => {
    const { container } = render(<OAuthButtons providers={providers({ magic_link: true })} />)
    expect(container).toBeEmptyDOMElement()
  })
})
