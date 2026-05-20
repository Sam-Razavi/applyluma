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
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
        <p className="mt-4 text-sm text-gray-500">Verifying your email…</p>
      </div>
    )
  }

  if (state === 'success') {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <CheckCircleIcon className="mx-auto h-16 w-16 text-green-500" />
          <h1 className="mt-4 text-2xl font-bold text-gray-900">Email verified!</h1>
          <p className="mt-2 text-sm text-gray-500">Your account is now active. You can sign in.</p>
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
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <XCircleIcon className="mx-auto h-16 w-16 text-red-400" />
        <h1 className="mt-4 text-2xl font-bold text-gray-900">Link invalid or expired</h1>
        <p className="mt-2 text-sm text-gray-500">
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
