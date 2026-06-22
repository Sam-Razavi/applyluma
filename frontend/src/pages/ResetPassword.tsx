import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/authApi'
import type { AxiosError } from 'axios'
import type { ApiError } from '../types'

const schema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full px-3 py-2.5 border border-line-strong rounded-lg text-sm placeholder-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    if (!token) {
      toast.error('Reset link is missing or invalid.')
      return
    }
    setIsSubmitting(true)
    try {
      await authApi.resetPassword(token, data.password)
      toast.success('Password reset successfully. Please sign in with your new password.')
      navigate('/login', { replace: true })
    } catch (err) {
      const axiosErr = err as AxiosError<ApiError>
      const message =
        axiosErr.response?.data?.detail ?? 'Reset link is invalid or has expired. Please request a new one.'
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-surface py-8 px-8 shadow-sm rounded-2xl border border-line text-center space-y-4">
            <p className="text-sm text-chip-danger-fg">This reset link is missing or invalid.</p>
            <Link to="/forgot-password" className="text-sm text-accent-text hover:underline font-medium">
              Request a new one
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 className="text-3xl font-bold text-fg tracking-tight">ApplyLuma</h1>
        <p className="mt-2 text-fg-subtle">Set a new password</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-surface py-8 px-8 shadow-sm rounded-2xl border border-line">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-fg-muted mb-1">
                New password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
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
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-fg-muted mb-1">
                Confirm new password
              </label>
              <div className="relative">
                <input
                  id="confirmPassword"
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Repeat password"
                  {...register('confirmPassword')}
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
              {errors.confirmPassword && (
                <p className="mt-1 text-xs text-chip-danger-fg">{errors.confirmPassword.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {isSubmitting ? 'Resetting...' : 'Reset password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
