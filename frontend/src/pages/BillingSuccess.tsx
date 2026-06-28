import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

const UNLOCKED = [
  '10 AI CV tailor runs per day',
  'Priority access to new job tools',
  'Premium analytics and optimization features',
]

export default function BillingSuccess() {
  const setUser = useAuthStore((state) => state.setUser)
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .finally(() => setLoading(false))
  }, [setUser])

  useEffect(() => {
    if (loading) return
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          navigate('/dashboard', { replace: true })
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [loading, navigate])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto max-w-xl rounded-2xl border border-line bg-surface p-8 text-center shadow-sm"
    >
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-chip-success">
        <CheckCircleIcon className="h-7 w-7 text-chip-success-fg" />
      </div>
      <h1 className="mt-4 text-xl font-semibold text-fg">Premium activated</h1>
      <p className="mt-2 text-sm text-fg-subtle">
        {loading
          ? 'Refreshing your account...'
          : 'Your Premium subscription is now active. Here\'s what you unlocked:'}
      </p>

      {!loading && (
        <ul className="mx-auto mt-4 max-w-xs space-y-2 text-left">
          {UNLOCKED.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-fg-muted">
              <SparklesIcon className="mt-0.5 h-4 w-4 shrink-0 text-accent-text" />
              {item}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 space-y-2">
        <Link
          to="/dashboard"
          className="inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Go to dashboard
        </Link>
        {!loading && (
          <p className="text-xs text-fg-subtle">
            Redirecting in {countdown}s...
          </p>
        )}
      </div>
    </motion.div>
  )
}
