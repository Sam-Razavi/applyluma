import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'
import type { AxiosError } from 'axios'
import type { ApiError } from '../types'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full px-3 py-2.5 border border-white/15 rounded-lg text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

const loginNotices: Record<string, { title: string; message: string }> = {
  'session-expired': {
    title: 'Session expired',
    message: 'Please sign in again to continue where you left off.',
  },
  inactive: {
    title: 'Signed out for inactivity',
    message: 'We signed you out after a period of inactivity to keep your account safe.',
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
  const loginNotice = loginNotices[searchParams.get('reason') ?? '']

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

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
    <div className="min-h-screen bg-white/[0.03] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="text-3xl font-bold text-white/90 tracking-tight hover:text-primary-300 transition-colors">ApplyLuma</Link>
        <p className="mt-2 text-white/30">Sign in to your account</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white/[0.04] py-8 px-8 shadow-sm rounded-2xl border border-white/10">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {serverError && (
              <div className="rounded-lg bg-[rgba(229,72,77,0.12)] border border-[rgba(229,72,77,0.18)] px-4 py-3">
                <p className="text-sm text-red-300">{serverError}</p>
              </div>
            )}

            {loginNotice && !serverError && (
              <div className="rounded-lg bg-[rgba(245,158,11,0.14)] border border-[rgba(245,158,11,0.20)] px-4 py-3">
                <p className="text-sm font-medium text-amber-300">{loginNotice.title}</p>
                <p className="mt-1 text-sm text-white/55">{loginNotice.message}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white/55 mb-1">
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
                <p className="mt-1 text-xs text-red-300">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white/55 mb-1">
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
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/55"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-300">{errors.password.message}</p>
              )}
              <div className="mt-1 text-right">
                <Link to="/forgot-password" className="text-xs text-primary-400 hover:underline">
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

          <p className="mt-6 text-center text-sm text-white/30">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-primary-400 hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
