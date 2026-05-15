import { Link } from 'react-router-dom'

export default function BillingCancel() {
  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-gray-900">Checkout canceled</h1>
      <p className="mt-2 text-sm text-gray-500">
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
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-200"
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}
