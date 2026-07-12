import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'
import { authApi as authExtraApi } from '../services/authApi'
import { useAuthStore } from '../stores'
import { useAuthProviders } from '../hooks/useAuthProviders'
import OAuthButtons from '../components/auth/OAuthButtons'
import type { AxiosError } from 'axios'
import type { ApiError } from '../types'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full px-3 py-2.5 border border-line-strong rounded-lg text-sm placeholder-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

const loginNotices: Record<string, { title: string; message: string }> = {
  'session-expired': {
    title: 'Session expired',
    message: 'Please sign in again to continue where you left off.',
  },
  inactive: {
    title: 'Signed out for inactivity',
    message: 'We signed you out after a period of inactivity to keep your account safe.',
  },
  oauth_failed: {
    title: 'Social sign-in failed',
    message: 'Something went wrong during sign-in with your provider. Please try again.',
  },
  magic_link_failed: {
    title: 'Sign-in link invalid',
    message: 'That sign-in link is invalid or has expired. Request a new one below.',
  },
}

function getSafeNextPath(nextPath: string | null) {
  if (!nextPath || !nextPath.startsWith('/') || nextPath.startsWith('//')) {
    return '/dashboard'
  }

  if (nextPath.startsWith('/login') || nextPath.startsWith('/register')) {
    return '/dashboard'
  }

  return nextPath
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, setToken } = useAuthStore()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [magicOpen, setMagicOpen] = useState(false)
  const [magicEmail, setMagicEmail] = useState('')
  const [magicSending, setMagicSending] = useState(false)
  const [magicSent, setMagicSent] = useState(false)
  const providers = useAuthProviders()
  const loginNotice = loginNotices[searchParams.get('reason') ?? searchParams.get('error') ?? '']

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault()
    if (!magicEmail.trim()) return
    setMagicSending(true)
    try {
      await authExtraApi.requestMagicLink(magicEmail.trim())
    } catch {
      // Same response either way: never reveal whether the account exists.
    } finally {
      // Anti-enumeration: identical confirmation whether or not the email matched.
      setMagicSent(true)
      setMagicSending(false)
    }
  }

  async function onSubmit(data: FormData) {
    setServerError(null)
    setIsSubmitting(true)
    try {
      const tokenPair = await authApi.login(data)
      // Store access token before calling /me so the axios interceptor can attach it.
      setToken(tokenPair.access_token)
      const user = await authApi.me()
      login(tokenPair.access_token, tokenPair.refresh_token, user)
      toast.success(`Welcome back${user.full_name ? ', ' + user.full_name.split(' ')[0] : ''}!`)
      navigate(getSafeNextPath(searchParams.get('next')), { replace: true })
    } catch (err) {
      const axiosErr = err as AxiosError<ApiError>
      const message = axiosErr.response?.data?.detail ?? 'Login failed. Please try again.'
      setServerError(message)
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="text-3xl font-bold text-fg tracking-tight hover:text-accent-text transition-colors">ApplyLuma</Link>
        <p className="mt-2 text-fg-subtle">Sign in to your account</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-8 shadow-sm rounded-2xl border border-line">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {serverError && (
              <div className="rounded-lg bg-chip-danger border border-chip-danger px-4 py-3">
                <p className="text-sm text-chip-danger-fg">{serverError}</p>
              </div>
            )}

            {loginNotice && !serverError && (
              <div className="rounded-lg bg-chip-warn border border-chip-warn px-4 py-3">
                <p className="text-sm font-medium text-chip-warn-fg">{loginNotice.title}</p>
                <p className="mt-1 text-sm text-fg-muted">{loginNotice.message}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-fg-muted mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                {...register('email')}
                className={inputClass}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-fg-muted mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="********"
                  {...register('password')}
                  className={inputClass}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg-muted"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.password.message}</p>
              )}
              <div className="mt-1 text-right">
                <Link to="/forgot-password" className="text-xs text-accent-text hover:underline">
                  Forgot password?
                </Link>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6">
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-surface" />
              <span className="text-xs text-fg-subtle">Or continue with</span>
              <div className="h-px flex-1 bg-surface" />
            </div>
            <div className="mt-4">
              <OAuthButtons providers={providers} />
            </div>
            {providers.magic_link && (
            <div className="mt-4 text-center">
              {magicSent ? (
                <p className="text-sm text-fg-subtle">
                  If an account exists for that email, a sign-in link is on its way.
                  Check your inbox.
                </p>
              ) : magicOpen ? (
                <form onSubmit={handleMagicLink} className="space-y-3 text-left">
                  <label htmlFor="magic-email" className="block text-sm font-medium text-fg-muted">
                    Email for your sign-in link
                  </label>
                  <input
                    id="magic-email"
                    type="email"
                    value={magicEmail}
                    onChange={(e) => setMagicEmail(e.target.value)}
                    placeholder="you@example.com"
                    className={inputClass}
                    autoFocus
                  />
                  <button
                    type="submit"
                    disabled={magicSending || !magicEmail.trim()}
                    className="w-full py-2.5 px-4 border border-line-strong rounded-lg text-sm font-medium text-fg hover:bg-surface-strong disabled:opacity-60 transition-colors"
                  >
                    {magicSending ? 'Sending…' : 'Email me a sign-in link'}
                  </button>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => setMagicOpen(true)}
                  className="text-sm font-medium text-accent-text hover:underline"
                >
                  Email me a sign-in link instead
                </button>
              )}
            </div>
            )}
          </div>

          <p className="mt-6 text-center text-sm text-fg-subtle">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-accent-text hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
