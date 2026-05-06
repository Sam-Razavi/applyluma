import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../stores'
import { authApi } from '../services/api'

export default function ProtectedRoute() {
  const { token, user, setUser, logout } = useAuthStore()
  const [checking, setChecking] = useState(!!token && !user)

  useEffect(() => {
    if (token && !user) {
      authApi
        .me()
        .then(setUser)
        .catch(logout)
        .finally(() => setChecking(false))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (!token) return <Navigate to="/login" replace />

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  return <Outlet />
}
