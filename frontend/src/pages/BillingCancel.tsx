import { Link } from 'react-router-dom'

export default function BillingCancel() {
  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-white/[0.04] p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-white/90">Checkout canceled</h1>
      <p className="mt-2 text-sm text-white/30">
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
          className="rounded-lg bg-white/[0.04] px-4 py-2 text-sm font-medium text-white/55 transition hover:bg-white/[0.08]"
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}
