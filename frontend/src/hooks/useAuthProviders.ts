import { useEffect, useState } from 'react'
import { authApi, type AuthProviders } from '../services/authApi'

// Shown until /auth/providers responds (and if it fails): matches the
// pre-multi-provider behavior of always offering Google.
export const FALLBACK_PROVIDERS: AuthProviders = {
  google: true,
  linkedin: false,
  github: false,
  magic_link: false,
}

/** Which login methods the backend has credentials for. */
export function useAuthProviders(): AuthProviders {
  const [providers, setProviders] = useState<AuthProviders>(FALLBACK_PROVIDERS)

  useEffect(() => {
    let cancelled = false
    authApi
      .getProviders()
      .then((result) => {
        if (!cancelled) setProviders(result)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  return providers
}
