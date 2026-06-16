import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '../services/authApi'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
})

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full px-3 py-2.5 border border-white/15 rounded-lg text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition'

export default function ForgotPassword() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setIsSubmitting(true)
    try {
      await authApi.forgotPassword(data.email)
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setIsSubmitting(false)
      setSubmitted(true)
    }
  }

  return (
    <div className="min-h-screen bg-white/[0.03] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 className="text-3xl font-bold text-white/90 tracking-tight">ApplyLuma</h1>
        <p className="mt-2 text-white/30">Reset your password</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white/[0.04] py-8 px-8 shadow-sm rounded-2xl border border-white/10">
          {submitted ? (
            <div className="text-center space-y-4">
              <div className="rounded-lg bg-[rgba(52,195,143,0.14)] border border-[rgba(52,195,143,0.22)] px-4 py-4">
                <p className="text-sm font-medium text-emerald-300">Check your inbox</p>
                <p className="mt-1 text-sm text-emerald-300">
                  If that email is registered, we've sent a password reset link. Check your spam folder if you don't see it within a minute.
                </p>
              </div>
              <Link to="/login" className="inline-block text-sm text-primary-400 hover:underline font-medium">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              <p className="text-sm text-white/55">
                Enter your email address and we'll send you a link to reset your password.
              </p>

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

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
              >
                {isSubmitting ? 'Sending...' : 'Send reset link'}
              </button>

              <p className="text-center text-sm text-white/30">
                <Link to="/login" className="font-medium text-primary-400 hover:underline">
                  Back to sign in
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
