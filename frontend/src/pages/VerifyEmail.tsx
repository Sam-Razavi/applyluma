import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/authApi'
import { useAuthStore } from '../stores'

type State = 'loading' | 'success' | 'error'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [state, setState] = useState<State>('loading')
  const setUser = useAuthStore((s) => s.setUser)

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setState('error')
      return
    }
    authApi.verifyEmail(token)
      .then((user) => {
        setUser(user)
        setState('success')
      })
      .catch(() => setState('error'))
  }, [searchParams, setUser])

  if (state === 'loading') {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-600/30 border-t-brand-600" />
        <p className="mt-4 text-sm text-fg-subtle">Verifying your email…</p>
      </div>
    )
  }

  if (state === 'success') {
    return (
      <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <CheckCircleIcon className="mx-auto h-16 w-16 text-chip-success-fg" />
          <h1 className="mt-4 text-2xl font-bold text-fg">Email verified!</h1>
          <p className="mt-2 text-sm text-fg-subtle">Your account is now active. You can sign in.</p>
          <Link
            to="/login"
            className="mt-6 inline-flex items-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            Go to sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <XCircleIcon className="mx-auto h-16 w-16 text-chip-danger-fg" />
        <h1 className="mt-4 text-2xl font-bold text-fg">Link invalid or expired</h1>
        <p className="mt-2 text-sm text-fg-subtle">
          This verification link has already been used or has expired.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Sign in to resend
        </Link>
      </div>
    </div>
  )
}
