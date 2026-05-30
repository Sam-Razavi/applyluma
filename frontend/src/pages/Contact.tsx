import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Turnstile, type TurnstileInstance } from '@marsidev/react-turnstile'
import toast from 'react-hot-toast'
import { CheckCircleIcon, EnvelopeIcon } from '@heroicons/react/24/outline'
import { contactApi } from '../services/api'
import type { AxiosError } from 'axios'
import type { ApiError } from '../types'

const TURNSTILE_SITE_KEY =
  import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '1x00000000000000000000AA'

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  email: z.string().email('Enter a valid email address'),
  subject: z.string().max(200).optional(),
  message: z.string().min(10, 'Message must be at least 10 characters').max(5000),
})

type FormData = z.infer<typeof schema>

const inputClass =
  'w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm placeholder-gray-400 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500 transition'

export default function Contact() {
  const [submitted, setSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null)
  const [honeypot, setHoneypot] = useState('')
  const turnstileRef = useRef<TurnstileInstance>(undefined)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    if (!turnstileToken) {
      toast.error('Please complete the CAPTCHA challenge.')
      return
    }
    setIsSubmitting(true)
    try {
      await contactApi.submit({
        name: data.name,
        email: data.email,
        subject: data.subject ?? '',
        message: data.message,
        turnstile_token: turnstileToken,
        honeypot,
      })
      setSubmitted(true)
    } catch (err) {
      const axiosErr = err as AxiosError<ApiError>
      toast.error(axiosErr.response?.data?.detail ?? 'Something went wrong. Please try again.')
      turnstileRef.current?.reset()
      setTurnstileToken(null)
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleSendAnother() {
    setSubmitted(false)
    setTurnstileToken(null)
    reset()
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Page header */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">Contact us</h1>
        <p className="mt-3 text-lg text-gray-500">
          Have a question or feedback? We'd love to hear from you.
        </p>
      </div>

      <div className="grid gap-10 lg:grid-cols-5">
        {/* ── Left: form ── */}
        <div className="lg:col-span-3">
          {submitted ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-green-200 bg-green-50 px-8 py-16 text-center">
              <CheckCircleIcon className="h-14 w-14 text-green-500" />
              <h2 className="mt-4 text-xl font-semibold text-gray-900">Message sent!</h2>
              <p className="mt-2 text-gray-500">
                We'll be in touch within 24 hours.
              </p>
              <button
                onClick={handleSendAnother}
                className="mt-6 text-sm font-medium text-primary-600 hover:text-primary-800 transition-colors"
              >
                Send another message →
              </button>
            </div>
          ) : (
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-700 dark:bg-gray-800"
            >
              <h2 className="mb-6 text-lg font-semibold text-gray-900 dark:text-white">
                Get in touch
              </h2>

              {/* Name + Email row */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('name')}
                    placeholder="Your name"
                    className={inputClass}
                  />
                  {errors.name && (
                    <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="you@example.com"
                    className={inputClass}
                  />
                  {errors.email && (
                    <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
                  )}
                </div>
              </div>

              {/* Subject */}
              <div className="mt-4">
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Subject
                </label>
                <input
                  {...register('subject')}
                  placeholder="What's this about? (optional)"
                  className={inputClass}
                />
              </div>

              {/* Message */}
              <div className="mt-4">
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Message <span className="text-red-500">*</span>
                </label>
                <textarea
                  {...register('message')}
                  rows={6}
                  placeholder="Tell us how we can help…"
                  className={`${inputClass} resize-none`}
                />
                {errors.message && (
                  <p className="mt-1 text-xs text-red-600">{errors.message.message}</p>
                )}
              </div>

              {/* Honeypot — hidden from real users, traps bots */}
              <input
                type="text"
                name="website"
                value={honeypot}
                onChange={(e) => setHoneypot(e.target.value)}
                autoComplete="off"
                tabIndex={-1}
                aria-hidden="true"
                style={{ position: 'absolute', left: '-9999px', width: '1px', height: '1px', opacity: 0 }}
              />

              {/* Turnstile */}
              <div className="mt-5">
                <Turnstile
                  ref={turnstileRef}
                  siteKey={TURNSTILE_SITE_KEY}
                  onSuccess={setTurnstileToken}
                  onError={() => setTurnstileToken(null)}
                  onExpire={() => setTurnstileToken(null)}
                  options={{ theme: 'light' }}
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !turnstileToken}
                className="mt-5 w-full rounded-lg bg-primary-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                {isSubmitting ? 'Sending…' : 'Send message →'}
              </button>
            </form>
          )}
        </div>

        {/* ── Right: info panel ── */}
        <aside className="lg:col-span-2">
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100">
              <EnvelopeIcon className="h-6 w-6 text-primary-600" />
            </div>

            <h3 className="mt-4 text-base font-semibold text-gray-900 dark:text-white">
              We're here to help
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Whether it's a question about pricing, a feature request, or just feedback — send us a
              message and we'll get back to you.
            </p>

            <div className="mt-6 space-y-4 border-t border-gray-100 pt-6 dark:border-gray-700">
              <div className="flex items-start gap-3">
                <EnvelopeIcon className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" />
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Email us at</p>
                  <a
                    href="mailto:sam@samincodes.com"
                    className="text-sm font-medium text-primary-600 hover:text-primary-800 transition-colors"
                  >
                    sam@samincodes.com
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Response time</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">Within 24 hours</p>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-xl bg-primary-50 p-4 dark:bg-primary-900/20">
              <p className="text-xs text-primary-700 dark:text-primary-300">
                Looking for help with the app? Check the{' '}
                <Link to="/dashboard" className="font-semibold underline underline-offset-2">
                  dashboard
                </Link>{' '}
                or{' '}
                <Link to="/plans" className="font-semibold underline underline-offset-2">
                  upgrade to Premium
                </Link>
                .
              </p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  )
}
