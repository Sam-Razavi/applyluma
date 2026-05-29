import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Analytics as VercelAnalytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { initTheme } from './stores/theme'
import { usePageTracking } from './hooks/usePageTracking'
import Layout from './components/layout/Layout'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import CheckEmail from './pages/CheckEmail'
import VerifyEmail from './pages/VerifyEmail'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import CVs from './pages/CVs'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import JobSearch from './pages/JobSearch'
import AITailor from './pages/AITailor'
import CoverLetter from './pages/CoverLetter'
import Analytics from './pages/Analytics'
import Discover from './pages/Discover'
import Settings from './pages/Settings'
import Plans from './pages/Plans'
import BillingSuccess from './pages/BillingSuccess'
import BillingCancel from './pages/BillingCancel'
import Contact from './pages/Contact'
import NotFound from './pages/NotFound'
import TermsOfService from './pages/TermsOfService'
import PrivacyPolicy from './pages/PrivacyPolicy'
import AdminRoute from './components/AdminRoute'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import { useAuthStore } from './stores'

export default function App() {
  const { token } = useAuthStore()
  usePageTracking()

  useEffect(() => { initTheme() }, [])

  return (
    <>
      <Routes>
        {/* Public pages with header + footer */}
        <Route element={<Layout />}>
          <Route index element={token ? <Navigate to="/dashboard" replace /> : <Home />} />
          <Route path="terms" element={<TermsOfService />} />
          <Route path="privacy" element={<PrivacyPolicy />} />
          <Route path="contact" element={<Contact />} />
        </Route>

        {/* Standalone auth pages (full-screen, no navbar) */}
        <Route
          path="login"
          element={token ? <Navigate to="/dashboard" replace /> : <Login />}
        />
        <Route
          path="register"
          element={token ? <Navigate to="/dashboard" replace /> : <Register />}
        />
        <Route path="check-email" element={<CheckEmail />} />
        <Route path="verify-email" element={<VerifyEmail />} />
        <Route path="forgot-password" element={<ForgotPassword />} />
        <Route path="reset-password" element={<ResetPassword />} />

        {/* Protected app shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="cvs" element={<CVs />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="discover" element={<Discover />} />
            <Route path="saved-jobs" element={<Navigate to="/jobs" replace />} />
            <Route path="job-search" element={<JobSearch />} />
            <Route path="applications" element={<Applications />} />
            <Route path="ai-tailor" element={<AITailor />} />
            <Route path="cover-letter" element={<CoverLetter />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
            <Route path="plans" element={<Plans />} />
            <Route path="billing/success" element={<BillingSuccess />} />
            <Route path="billing/cancel" element={<BillingCancel />} />
            <Route element={<AdminRoute />}>
              <Route path="admin" element={<AdminDashboard />} />
              <Route path="admin/users" element={<AdminUsers />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      <VercelAnalytics />
      <SpeedInsights />
    </>
  )
}

