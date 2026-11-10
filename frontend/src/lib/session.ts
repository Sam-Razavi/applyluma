// Restoring a sign-in in a new tab.
//
// The auth store persists to sessionStorage, which is per tab, so a new tab
// (an extension button, a bookmark, a link in an email) starts signed out even
// though the httpOnly refresh cookie is still valid. These helpers trade that
// cookie for a session instead of sending the user to the login page.

import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

const HINT_KEY = 'applyluma_signed_in'

// A non-secret flag (written by the auth store on login/logout) that this
// browser has signed in, so public pages (the landing page, /login) only spend
// a request on restoring when it can work.
export function hasSignedInHint(): boolean {
  try {
    return localStorage.getItem(HINT_KEY) === '1'
  } catch {
    return false
  }
}

let inFlight: Promise<boolean> | null = null
let attempted = false

/**
 * Sign in from the refresh cookie, once per page load (when a tab opens).
 * Resolves false when there is no valid session.
 *
 * Only once: after signing out in this tab, the next protected page must show
 * the login page, even if the server-side logout failed and the cookie lives on.
 */
export function restoreSession(): Promise<boolean> {
  if (useAuthStore.getState().isAuthenticated) return Promise.resolve(true)
  if (inFlight) return inFlight
  if (attempted) return Promise.resolve(false)
  attempted = true
  inFlight = (async () => {
    try {
      const { access_token } = await authApi.refresh()
      useAuthStore.getState().setToken(access_token)
      const user = await authApi.me()
      useAuthStore.getState().login(access_token, '', user)
      return true
    } catch {
      useAuthStore.getState().logout()
      return false
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

/** Test-only: forget that this page load already tried. */
export function resetRestoreForTests(): void {
  attempted = false
  inFlight = null
}
