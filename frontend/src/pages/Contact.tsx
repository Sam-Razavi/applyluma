import { useEffect, useRef, useState } from 'react'
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
  'w-full rounded-lg border border-line-strong px-3 py-2.5 text-sm placeholder-fg-subtle shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 transition'

export default function Contact() {
  useEffect(() => {
    document.title = 'Contact — ApplyLuma'
  }, [])

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
        honeypot,
        turnstile_token: turnstileToken,
      })
      setSubmitted(true)
    } catch (err) {
      const msg = err instanceof Error
        ? err.message
        : (err as AxiosError<ApiError>).response?.data?.detail ?? 'Something went wrong. Please try again.'
      toast.error(msg)
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
        <h1 className="text-4xl font-bold tracking-tight text-fg">Contact us</h1>
        <p className="mt-3 text-lg text-fg-subtle">
          Have a question or feedback? We'd love to hear from you.
        </p>
      </div>

      <div className="grid gap-10 lg:grid-cols-5">
        {/* ── Left: form ── */}
        <div className="lg:col-span-3">
          {submitted ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-chip-success bg-chip-success px-8 py-16 text-center">
              <CheckCircleIcon className="h-14 w-14 text-chip-success-fg" />
              <h2 className="mt-4 text-xl font-semibold text-fg">Message sent!</h2>
              <p className="mt-2 text-fg-subtle">
                We'll be in touch within 24 hours.
              </p>
              <button
                onClick={handleSendAnother}
                className="mt-6 text-sm font-medium text-accent-text hover:text-primary-800 transition-colors"
              >
                Send another message →
              </button>
            </div>
          ) : (
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="rounded-2xl border border-line bg-surface p-8 shadow-sm "
            >
              <h2 className="mb-6 text-lg font-semibold text-fg ">
                Get in touch
              </h2>

              {/* Name + Email row */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-fg-muted ">
                    Name <span className="text-chip-danger-fg">*</span>
                  </label>
                  <input
                    {...register('name')}
                    placeholder="Your name"
                    className={inputClass}
                  />
                  {errors.name && (
                    <p className="mt-1 text-xs text-chip-danger-fg">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-fg-muted ">
                    Email <span className="text-chip-danger-fg">*</span>
                  </label>
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="you@example.com"
                    className={inputClass}
                  />
                  {errors.email && (
                    <p className="mt-1 text-xs text-chip-danger-fg">{errors.email.message}</p>
                  )}
                </div>
              </div>

              {/* Subject */}
              <div className="mt-4">
                <label className="mb-1.5 block text-sm font-medium text-fg-muted ">
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
                <label className="mb-1.5 block text-sm font-medium text-fg-muted ">
                  Message <span className="text-chip-danger-fg">*</span>
                </label>
                <textarea
                  {...register('message')}
                  rows={6}
                  placeholder="Tell us how we can help…"
                  className={`${inputClass} resize-none`}
                />
                {errors.message && (
                  <p className="mt-1 text-xs text-chip-danger-fg">{errors.message.message}</p>
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
          <div className="rounded-2xl border border-line bg-surface p-8 shadow-sm ">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100">
              <EnvelopeIcon className="h-6 w-6 text-accent-text" />
            </div>

            <h3 className="mt-4 text-base font-semibold text-fg ">
              We're here to help
            </h3>
            <p className="mt-2 text-sm text-fg-subtle ">
              Whether it's a question about pricing, a feature request, or just feedback — send us a
              message and we'll get back to you.
            </p>

            <div className="mt-6 space-y-4 border-t border-line pt-6 ">
              <div className="flex items-start gap-3">
                <EnvelopeIcon className="mt-0.5 h-5 w-5 shrink-0 text-fg-subtle" />
                <div>
                  <p className="text-xs font-medium text-fg-subtle ">Email us at</p>
                  <a
                    href="mailto:sam@samincodes.com"
                    className="text-sm font-medium text-accent-text hover:text-primary-800 transition-colors"
                  >
                    sam@samincodes.com
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-xs font-medium text-fg-subtle ">Response time</p>
                  <p className="text-sm text-fg-muted ">Within 24 hours</p>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-xl bg-primary-900/20 p-4 ">
              <p className="text-xs text-accent-text ">
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
