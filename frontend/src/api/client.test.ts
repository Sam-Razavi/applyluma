import { describe, it, expect, beforeEach } from 'vitest'
import type { InternalAxiosRequestConfig } from 'axios'
import { AxiosHeaders } from 'axios'
import client from './client'
import { useAuthStore } from '../stores'

// Run the request interceptors on a config without sending anything.
async function prepare(url: string): Promise<InternalAxiosRequestConfig> {
  let config = { url, method: 'get', headers: new AxiosHeaders() } as InternalAxiosRequestConfig
  const handlers = (client.interceptors.request as unknown as {
    handlers: { fulfilled: (c: InternalAxiosRequestConfig) => InternalAxiosRequestConfig }[]
  }).handlers
  for (const handler of handlers) config = await handler.fulfilled(config)
  return config
}

describe('API client', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('sends the login token to /analytics endpoints too', async () => {
    // /analytics/freshness needs a signed-in user; without the header it relied
    // on a cookie that Google sign-in sets on another host, and the 401 logged
    // Google users out as soon as the dashboard loaded.
    useAuthStore.getState().setToken('access-123')

    const config = await prepare('/api/v1/analytics/freshness')

    expect(config.headers.Authorization).toBe('Bearer access-123')
  })

  it('sends no Authorization header when signed out', async () => {
    const config = await prepare('/api/v1/analytics/job-market-health')

    expect(config.headers.Authorization).toBeUndefined()
  })
})
