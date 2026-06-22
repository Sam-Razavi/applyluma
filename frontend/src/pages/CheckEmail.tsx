import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { EnvelopeIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { authApi } from '../services/authApi'

export default function CheckEmail() {
  const location = useLocation()
  const email = (location.state as { email?: string } | null)?.email
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)

  async function handleResend() {
    setResending(true)
    try {
      await authApi.resendVerification()
      setResent(true)
      toast.success('Verification email sent!')
    } catch {
      toast.error('Could not resend. Please sign in first.')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary-900/30">
          <EnvelopeIcon className="h-8 w-8 text-accent-text" />
        </div>
        <h1 className="mt-6 text-2xl font-bold text-fg">Check your email</h1>
        <p className="mt-3 text-sm text-fg-subtle">
          We sent a verification link to{' '}
          {email ? <span className="font-medium text-fg-muted">{email}</span> : 'your email address'}.
          Click it to activate your account.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-8 shadow-sm rounded-2xl border border-line text-center space-y-4">
          <p className="text-sm text-fg-subtle">Didn't get it? Check your spam folder, or</p>
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || resent}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {resent ? 'Email sent ✓' : resending ? 'Sending…' : 'Resend verification email'}
          </button>
          <p className="text-xs text-fg-subtle">
            Already verified?{' '}
            <Link to="/login" className="font-medium text-accent-text hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
