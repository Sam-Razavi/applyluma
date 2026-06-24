import { lazy, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Analytics as VercelAnalytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { initTheme } from './stores/theme'
import { usePageTracking } from './hooks/usePageTracking'
import { useCookieConsent } from './hooks/useCookieConsent'
import { CookieBanner } from './components/ui/CookieBanner'
import Layout from './components/layout/Layout'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import RouteFallback from './components/ui/RouteFallback'
import { useAuthStore } from './stores'

// First-paint entry points stay eager to avoid a fallback flash on the most
// common landing routes. Everything else is lazy-loaded as its own chunk.
import Home from './pages/Home'
import Login from './pages/Login'

const Register = lazy(() => import('./pages/Register'))
const CheckEmail = lazy(() => import('./pages/CheckEmail'))
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const ExtensionAuth = lazy(() => import('./pages/ExtensionAuth'))
const AuthCallback = lazy(() => import('./pages/AuthCallback'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CVs = lazy(() => import('./pages/CVs'))
const Jobs = lazy(() => import('./pages/Jobs'))
const Applications = lazy(() => import('./pages/Applications'))
const AITailor = lazy(() => import('./pages/AITailor'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Discover = lazy(() => import('./pages/Discover'))
const Settings = lazy(() => import('./pages/Settings'))
const Plans = lazy(() => import('./pages/Plans'))
const BillingSuccess = lazy(() => import('./pages/BillingSuccess'))
const BillingCancel = lazy(() => import('./pages/BillingCancel'))
const Contact = lazy(() => import('./pages/Contact'))
const NotFound = lazy(() => import('./pages/NotFound'))
const TermsOfService = lazy(() => import('./pages/TermsOfService'))
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy'))
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'))
const AdminPipeline = lazy(() => import('./pages/admin/AdminPipeline'))
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'))

export default function App() {
  const { isAuthenticated } = useAuthStore()
  const { consent, accept, decline } = useCookieConsent()
  usePageTracking()

  useEffect(() => { initTheme() }, [])

  return (
    <>
      <ErrorBoundary>
        <Suspense fallback={<RouteFallback fullPage />}>
          <Routes>
        {/* Public pages with header + footer */}
        <Route element={<Layout />}>
          <Route index element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Home />} />
          <Route path="terms" element={<TermsOfService />} />
          <Route path="privacy" element={<PrivacyPolicy />} />
          <Route path="contact" element={<Contact />} />
        </Route>

        {/* Standalone auth pages (full-screen, no navbar) */}
        <Route
          path="login"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
        />
        <Route
          path="register"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />}
        />
        <Route path="check-email" element={<CheckEmail />} />
        <Route path="verify-email" element={<VerifyEmail />} />
        <Route path="forgot-password" element={<ForgotPassword />} />
        <Route path="reset-password" element={<ResetPassword />} />
        <Route path="extension-auth" element={<ExtensionAuth />} />
        <Route path="auth/callback" element={<AuthCallback />} />

        {/* Protected app shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<ErrorBoundary><AppLayout /></ErrorBoundary>}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="cvs" element={<CVs />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="discover" element={<Discover />} />
            <Route path="saved-jobs" element={<Navigate to="/jobs" replace />} />
            <Route path="job-search" element={<Navigate to="/discover?tab=search" replace />} />
            <Route path="applications" element={<Applications />} />
            <Route path="ai-tailor" element={<AITailor />} />
            <Route path="cover-letter" element={<Navigate to="/ai-tailor" replace />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
            <Route path="plans" element={<Plans />} />
            <Route path="billing/success" element={<BillingSuccess />} />
            <Route path="billing/cancel" element={<BillingCancel />} />
            <Route element={<AdminRoute />}>
              <Route path="admin" element={<AdminDashboard />} />
              <Route path="admin/users" element={<AdminUsers />} />
              <Route path="admin/pipeline" element={<AdminPipeline />} />
            </Route>
          </Route>
        </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>

      {/* Analytics only after explicit consent */}
      {consent === 'accepted' && <VercelAnalytics />}
      {consent === 'accepted' && <SpeedInsights />}

      <CookieBanner consent={consent} onAccept={accept} onDecline={decline} />
    </>
  )
}
