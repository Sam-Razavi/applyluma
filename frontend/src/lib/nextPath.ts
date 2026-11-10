// Where to send someone after they sign in. Kept in sessionStorage as well as
// the ?next= query, because Google/LinkedIn/GitHub sign-in leaves the site and
// comes back through /auth/callback, which never sees the original query.

const KEY = 'applyluma_next_path'

export function getSafeNextPath(nextPath: string | null): string {
  if (!nextPath || !nextPath.startsWith('/') || nextPath.startsWith('//')) {
    return '/dashboard'
  }
  if (nextPath.startsWith('/login') || nextPath.startsWith('/register')) {
    return '/dashboard'
  }
  return nextPath
}

export function rememberNextPath(nextPath: string | null): void {
  const safe = getSafeNextPath(nextPath)
  try {
    if (safe === '/dashboard') sessionStorage.removeItem(KEY)
    else sessionStorage.setItem(KEY, safe)
  } catch {
    // Storage blocked: sign-in still works, it just lands on the dashboard.
  }
}

/** The remembered destination (or /dashboard), cleared so it is used once. */
export function consumeNextPath(): string {
  let stored: string | null = null
  try {
    stored = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
  } catch {
    stored = null
  }
  return getSafeNextPath(stored)
}
