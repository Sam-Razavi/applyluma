import { useEffect, useState } from 'react'
import { Navigate, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores'
import { authApi } from '../services/api'

export default function ProtectedRoute() {
  const { isAuthenticated, user, setUser, logout } = useAuthStore()
  const navigate = useNavigate()
  // Fetch /me when the store says we're authenticated but has no user object
  // (e.g. sessionStorage cleared but httpOnly cookie still valid).
  const [checking, setChecking] = useState(isAuthenticated && !user)

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

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  return <Outlet />
}
