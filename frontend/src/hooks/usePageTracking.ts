import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import posthog from 'posthog-js'

// Routes that must never be sent to PostHog: the OAuth callback URL can
// carry a live access token (in the fragment), and window.location.href
// includes fragments — capturing it would leak the token to a third party.
const UNTRACKED_PATHS = new Set(['/auth/callback'])

export function usePageTracking() {
  const location = useLocation()

  useEffect(() => {
    if (UNTRACKED_PATHS.has(location.pathname)) return
    posthog.capture('$pageview', { $current_url: window.location.href })
  }, [location.pathname, location.search])
}
