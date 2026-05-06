import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import CVs from './pages/CVs'
import Jobs from './pages/Jobs'
import NotFound from './pages/NotFound'
import { useAuthStore } from './stores'

export default function App() {
  const { token } = useAuthStore()

  return (
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
          <Route path="ai-tailor" element={<ComingSoon label="AI Tailor" />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-4xl mb-4">🚧</p>
      <h2 className="text-xl font-semibold text-gray-900">{label}</h2>
      <p className="mt-2 text-sm text-gray-500">This page is coming in the next phase.</p>
    </div>
  )
}
