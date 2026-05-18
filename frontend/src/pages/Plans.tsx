import { useState } from 'react'
import toast from 'react-hot-toast'
import PlanCard from '../components/billing/PlanCard'
import { createCheckoutSession, createPortalSession } from '../services/billingApi'
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

export default function Plans() {
  const { user } = useAuthStore()
  const [loading, setLoading] = useState<'checkout' | 'portal' | null>(null)
  const isPremium = user?.role === 'premium' || user?.role === 'admin'

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

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Plans</h1>
        <p className="mt-1 text-sm text-gray-500">
          Choose the plan that fits your job search workflow.
        </p>
      </div>

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
          onClick={isPremium ? handleManageBilling : handleUpgrade}
        />
      </div>

      {isPremium && (
        <div className="rounded-2xl border border-green-200 bg-green-50 px-5 py-4">
          <p className="text-sm font-medium text-green-900">
            Your account is currently on {user?.role === 'admin' ? 'admin' : 'premium'} access.
          </p>
        </div>
      )}
    </div>
  )
}
