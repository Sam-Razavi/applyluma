import posthog from 'posthog-js'

let _initialized = false

/** Initialize PostHog once. Safe to call multiple times. */
export function initAnalytics(): void {
  if (_initialized) return
  const key = import.meta.env.VITE_POSTHOG_KEY as string | undefined
  if (key) {
    posthog.init(key, {
      api_host: (import.meta.env.VITE_POSTHOG_HOST as string | undefined) ?? 'https://eu.i.posthog.com',
      capture_pageview: false,
      persistence: 'localStorage',
    })
    _initialized = true
  }
}
