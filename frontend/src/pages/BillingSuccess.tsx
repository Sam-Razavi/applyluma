import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircleIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

export default function BillingSuccess() {
  const setUser = useAuthStore((state) => state.setUser)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .finally(() => setLoading(false))
  }, [setUser])

  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-line bg-surface p-8 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-chip-success">
        <CheckCircleIcon className="h-7 w-7 text-chip-success-fg" />
      </div>
      <h1 className="mt-4 text-xl font-semibold text-fg">Premium activated</h1>
      <p className="mt-2 text-sm text-fg-subtle">
        {loading
          ? 'Refreshing your account...'
          : 'Your account has been refreshed with the latest billing status.'}
      </p>
      <Link
        to="/dashboard"
        className="mt-6 inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        Back to dashboard
      </Link>
    </div>
  )
}
