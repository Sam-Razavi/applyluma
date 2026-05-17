import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Analytics as VercelAnalytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/react'
import { initTheme } from './stores/theme'
import Layout from './components/layout/Layout'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import CVs from './pages/CVs'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import JobSearch from './pages/JobSearch'
import AITailor from './pages/AITailor'
import Analytics from './pages/Analytics'
import Discover from './pages/Discover'
import SavedJobs from './pages/SavedJobs'
import Settings from './pages/Settings'
import Plans from './pages/Plans'
import BillingSuccess from './pages/BillingSuccess'
import BillingCancel from './pages/BillingCancel'
import NotFound from './pages/NotFound'
import { useAuthStore } from './stores'

export default function App() {
  const { token } = useAuthStore()

  useEffect(() => { initTheme() }, [])

  return (
    <>
      <Routes>
        {/* Marketing page — redirect authenticated users straight to app */}
        <Route element={<Layout />}>
          <Route index element={token ? <Navigate to="/dashboard" replace /> : <Home />} />
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

        {/* Protected app shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="cvs" element={<CVs />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="discover" element={<Discover />} />
            <Route path="saved-jobs" element={<SavedJobs />} />
            <Route path="job-search" element={<JobSearch />} />
            <Route path="applications" element={<Applications />} />
            <Route path="ai-tailor" element={<AITailor />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
            <Route path="plans" element={<Plans />} />
            <Route path="billing/success" element={<BillingSuccess />} />
            <Route path="billing/cancel" element={<BillingCancel />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      <VercelAnalytics />
      <SpeedInsights />
    </>
  )
}

