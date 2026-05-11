import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
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
  'w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

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
  const loginNotice = loginNotices[searchParams.get('reason') ?? '']

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setServerError(null)
    setIsSubmitting(true)
    console.log('[Login] attempting login for:', data.email)
    try {
      const tokenPair = await authApi.login(data)
      console.log('[Login] token received:', tokenPair.access_token ? 'present' : 'missing')

      // Store token before calling /me so the axios interceptor can attach it.
      setToken(tokenPair.access_token)
      console.log('[Login] token stored in store, store token now:', !!useAuthStore.getState().token)

      console.log('[Login] calling GET /api/v1/auth/me...')
      const user = await authApi.me()
      console.log('[Login] user fetched:', user.email)
      login(tokenPair.access_token, user)
      toast.success(`Welcome back${user.full_name ? ', ' + user.full_name.split(' ')[0] : ''}!`)
      navigate(getSafeNextPath(searchParams.get('next')), { replace: true })
    } catch (err) {
      console.error('[Login] error:', err)
      const axiosErr = err as AxiosError<ApiError>
      const message = axiosErr.response?.data?.detail ?? 'Login failed. Please try again.'
      setServerError(message)
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">ApplyLuma</h1>
        <p className="mt-2 text-gray-500">Sign in to your account</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-8 shadow-sm rounded-2xl border border-gray-200">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {serverError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                <p className="text-sm text-red-700">{serverError}</p>
              </div>
            )}

            {loginNotice && !serverError && (
              <div className="rounded-lg bg-warning-50 border border-warning-500/30 px-4 py-3">
                <p className="text-sm font-medium text-warning-600">{loginNotice.title}</p>
                <p className="mt-1 text-sm text-gray-600">{loginNotice.message}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
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
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="********"
                {...register('password')}
                className={inputClass}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-brand-600 hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
