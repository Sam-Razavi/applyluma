import { useEffect, useState } from 'react'
import {
  ExclamationTriangleIcon,
  BeakerIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import PlanCard from '../components/billing/PlanCard'
import { createCheckoutSession, createPortalSession, getBillingStatus } from '../services/billingApi'
import { useAuthStore } from '../stores'

const FREE_FEATURES = [
  '1 AI CV tailor run per day',
  'Application tracking board',
  'Market analytics dashboard',
  'CV and job description management',
]

const PREMIUM_FEATURES = [
  '10 AI CV tailor runs per day',
  'Priority access to new job tools',
  'Full application tracking workflow',
  'Premium analytics and optimization features',
]

const FAQ = [
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. You can cancel your subscription at any time from the billing portal. You keep Premium access until the end of your current billing period.',
  },
  {
    q: 'What happens when I downgrade?',
    a: 'Your daily AI CV tailor limit goes back to 1 per day. All your saved data, applications, and CVs stay intact.',
  },
  {
    q: 'How do refunds work?',
    a: 'We process refunds on a case-by-case basis. Contact us at support@applyluma.com within 14 days of your payment.',
  },
]

export default function Plans() {
  const { user } = useAuthStore()
  const [loading, setLoading] = useState<'checkout' | 'portal' | null>(null)
  const [billingStatus, setBillingStatus] = useState<{ configured: boolean; test_mode: boolean } | null>(null)
  const isPremium = user?.role === 'premium' || user?.role === 'admin'
  const isPastDue = user?.subscription_status === 'past_due'

  useEffect(() => {
    getBillingStatus().then(setBillingStatus).catch(() => {})
  }, [])

  async function handleUpgrade() {
    setLoading('checkout')
    try {
      const { checkout_url } = await createCheckoutSession()
      window.location.href = checkout_url
    } catch {
      toast.error('Could not open Stripe Checkout')
      setLoading(null)
    }
  }

  async function handleManageBilling() {
    setLoading('portal')
    try {
      const { portal_url } = await createPortalSession()
      window.location.href = portal_url
    } catch {
      toast.error('Could not open billing portal')
      setLoading(null)
    }
  }

  const stripeReady = billingStatus?.configured ?? true

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-fg">Plans</h1>
          {billingStatus?.test_mode && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-400">
              <BeakerIcon className="h-3.5 w-3.5" />
              Test mode
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-fg-subtle">
          Choose the plan that fits your job search workflow.
        </p>
      </div>

      {billingStatus && !billingStatus.configured && (
        <div className="flex items-start gap-3 rounded-2xl border border-line bg-surface px-5 py-4">
          <InformationCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-fg-subtle" />
          <p className="text-sm text-fg-muted">
            Stripe is not configured yet. Set <code className="text-xs">STRIPE_SECRET_KEY</code>,{' '}
            <code className="text-xs">STRIPE_WEBHOOK_SECRET</code>, and{' '}
            <code className="text-xs">STRIPE_PREMIUM_PRICE_ID</code> in your environment to enable checkout.
          </p>
        </div>
      )}

      {isPastDue && (
        <div className="flex items-start gap-3 rounded-2xl border border-chip-danger bg-chip-danger px-5 py-4">
          <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-chip-danger-fg" />
          <div>
            <p className="text-sm font-medium text-chip-danger-fg">
              Your last payment failed. Update your payment method to keep Premium access.
            </p>
            <button
              type="button"
              onClick={() => void handleManageBilling()}
              disabled={loading !== null}
              className="mt-2 text-sm font-semibold text-chip-danger-fg underline hover:no-underline"
            >
              Manage billing
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-6 md:flex-row">
        <PlanCard
          name="Free"
          price="$0"
          description="For getting started with CV tailoring and application tracking."
          features={FREE_FEATURES}
          ctaLabel={isPremium ? 'Current baseline' : 'Current plan'}
          disabled
        />
        <PlanCard
          name="Premium"
          price="$9.99/mo"
          description="For active job seekers who tailor more CVs and want more capacity."
          features={PREMIUM_FEATURES}
          highlighted
          ctaLabel={isPremium ? 'Manage billing' : 'Upgrade'}
          loading={loading !== null}
          disabled={!stripeReady && !isPremium}
          onClick={isPremium ? handleManageBilling : handleUpgrade}
        />
      </div>

      {isPremium && (
        <div className="rounded-2xl border border-chip-success bg-chip-success px-5 py-4">
          <p className="text-sm font-medium text-chip-success-fg">
            Your account is currently on {user?.role === 'admin' ? 'admin' : 'premium'} access.
          </p>
        </div>
      )}

      {/* FAQ */}
      <div>
        <h2 className="text-lg font-semibold text-fg">Frequently asked questions</h2>
        <dl className="mt-4 space-y-4">
          {FAQ.map(({ q, a }) => (
            <div key={q} className="rounded-2xl border border-line bg-surface px-5 py-4">
              <dt className="text-sm font-medium text-fg">{q}</dt>
              <dd className="mt-1 text-sm text-fg-muted">{a}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}
