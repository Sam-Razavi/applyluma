import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores'
import { authApi } from '../services/api'
import { restoreSession } from '../lib/session'
import RouteFallback from './ui/RouteFallback'

export default function ProtectedRoute() {
  const { isAuthenticated, user, setUser, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  // A new tab has no session of its own yet, but the httpOnly refresh cookie
  // may still be valid: try that before sending anyone to the login page.
  const [restoring, setRestoring] = useState(!isAuthenticated)
  // Fetch /me when the store says we're authenticated but has no user object
  // (e.g. sessionStorage cleared but httpOnly cookie still valid).
  const [checking, setChecking] = useState(isAuthenticated && !user)

  useEffect(() => {
    if (isAuthenticated) {
      setRestoring(false)
      return
    }
    let active = true
    setRestoring(true)
    void restoreSession().finally(() => {
      if (active) setRestoring(false)
    })
    return () => {
      active = false
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated || user) {
      setChecking(false)
      return
    }

    let active = true
    setChecking(true)

    authApi
      .me()
      .then((currentUser) => {
        if (active) setUser(currentUser)
      })
      .catch(() => {
        if (!active) return
        logout()
        navigate('/login?reason=session-expired', { replace: true })
      })
      .finally(() => {
        if (active) setChecking(false)
      })

    return () => {
      active = false
    }
  }, [logout, navigate, setUser, isAuthenticated, user])

  if (restoring || checking) return <RouteFallback fullPage />

  if (!isAuthenticated) {
    // Come back here after signing in (e.g. /discover?tab=saved from the extension).
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }

  return <Outlet />
}
