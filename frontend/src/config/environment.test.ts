import { afterEach, describe, expect, it, vi } from 'vitest'

describe('config.apiUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('drops a trailing slash so joined paths have a single slash', async () => {
    vi.stubEnv('VITE_API_URL', 'https://api.applyluma.com/')
    const { config } = await import('./environment')
    expect(config.apiUrl).toBe('https://api.applyluma.com')
    expect(`${config.apiUrl}/api/v1/auth/google/login`).toBe(
      'https://api.applyluma.com/api/v1/auth/google/login',
    )
  })

  it('leaves a URL without a trailing slash unchanged', async () => {
    vi.stubEnv('VITE_API_URL', 'https://api.applyluma.com')
    const { config } = await import('./environment')
    expect(config.apiUrl).toBe('https://api.applyluma.com')
  })
})
