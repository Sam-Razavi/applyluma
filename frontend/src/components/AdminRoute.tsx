import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../stores'

export default function AdminRoute() {
  const { user } = useAuthStore()
  if (!user) return null
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <Outlet />
}
