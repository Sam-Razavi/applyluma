import { Navigate, Outlet } from 'react-router-dom'
import AdminStatusBanner from './layout/AdminStatusBanner'
import { useAuthStore } from '../stores'

export default function AdminRoute() {
  const { user } = useAuthStore()
  if (!user) return null
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return (
    <>
      <AdminStatusBanner />
      <Outlet />
    </>
  )
}
