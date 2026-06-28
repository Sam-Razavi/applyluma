import { Link } from 'react-router-dom'
import { SparklesIcon } from '@heroicons/react/24/outline'

export default function BillingCancel() {
  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-line bg-surface p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-fg">Checkout canceled</h1>
      <p className="mt-2 text-sm text-fg-subtle">
        No changes were made to your account.
      </p>

      <div className="mx-auto mt-5 max-w-xs rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-3 text-left">
        <p className="flex items-center gap-1.5 text-sm font-medium text-accent-text">
          <SparklesIcon className="h-4 w-4" />
          Premium gives you 10x more AI CV tailors per day
        </p>
        <p className="mt-1 text-xs text-fg-muted">
          Plus priority access to new tools and premium analytics.
        </p>
      </div>

      <div className="mt-6 flex justify-center gap-2">
        <Link
          to="/plans"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          View plans
        </Link>
        <Link
          to="/dashboard"
          className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition hover:bg-surface-strong"
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}
