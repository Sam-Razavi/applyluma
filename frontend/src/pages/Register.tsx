import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'
import type { AxiosError } from 'axios'
import type { ApiError } from '../types'
import OAuthButtons from '../components/auth/OAuthButtons'
import { useAuthProviders } from '../hooks/useAuthProviders'
import { PasswordStrengthMeter } from '../components/auth/PasswordStrengthMeter'

const schema = z
  .object({
    full_name: z.string().optional(),
    email: z.string().email('Enter a valid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Include at least one uppercase letter')
      .regex(/[0-9]/, 'Include at least one number'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full px-3 py-2.5 border border-line-strong rounded-lg text-sm placeholder-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

export default function Register() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const providers = useAuthProviders()

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const passwordValue = watch('password', '')

  async function onSubmit(data: FormData) {
    setIsSubmitting(true)
    try {
      await authApi.register({
        email: data.email,
        password: data.password,
        full_name: data.full_name?.trim() || undefined,
      })
      navigate('/check-email', { state: { email: data.email } })
    } catch (err) {
      const axiosErr = err as AxiosError<ApiError>
      toast.error(axiosErr.response?.data?.detail ?? 'Registration failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="text-3xl font-bold text-fg tracking-tight hover:text-accent-text transition-colors">ApplyLuma</Link>
        <p className="mt-2 text-fg-subtle">Create your free account</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-8 shadow-sm rounded-2xl border border-line">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-fg-muted mb-1">
                Full name{' '}
                <span className="text-fg-subtle font-normal">(optional)</span>
              </label>
              <input
                id="full_name"
                type="text"
                autoComplete="name"
                placeholder="Jane Smith"
                {...register('full_name')}
                className={inputClass}
              />
              {errors.full_name && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.full_name.message}</p>
              )}
            </div>

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
                  autoComplete="new-password"
                  placeholder="Min 8 chars, 1 uppercase, 1 number"
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
              <PasswordStrengthMeter password={passwordValue} />
              {errors.password && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-fg-muted mb-1">
                Confirm password
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  {...register('confirm_password')}
                  className={inputClass}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg-muted"
                  aria-label={showConfirm ? 'Hide password' : 'Show password'}
                >
                  {showConfirm ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.confirm_password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <div className="mt-6">
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-line" />
              <span className="text-xs text-fg-subtle">Or continue with</span>
              <div className="h-px flex-1 bg-line" />
            </div>
            <div className="mt-4">
              <OAuthButtons providers={providers} />
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-fg-subtle">
            By creating an account, you agree to our{' '}
            <Link to="/terms" className="font-medium text-accent-text hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" className="font-medium text-accent-text hover:underline">
              Privacy Policy
            </Link>
            .
          </p>

          <p className="mt-4 text-center text-sm text-fg-subtle">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-accent-text hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
