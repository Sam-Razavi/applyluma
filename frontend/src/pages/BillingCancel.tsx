import { Link } from 'react-router-dom'

export default function BillingCancel() {
  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-line bg-surface p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-fg">Checkout canceled</h1>
      <p className="mt-2 text-sm text-fg-subtle">
        No changes were made to your account.
      </p>
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
