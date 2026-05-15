import { Link } from 'react-router-dom'

interface Props {
  title?: string
  message?: string
}

export default function UpgradePrompt({
  title = 'Upgrade to Premium',
  message = 'Unlock higher daily tailoring limits and premium job search tools.',
}: Props) {
  return (
    <div className="rounded-2xl border border-brand-200 bg-brand-50 p-4">
      <h3 className="text-sm font-semibold text-brand-900">{title}</h3>
      <p className="mt-1 text-sm text-brand-700">{message}</p>
      <Link
        to="/plans"
        className="mt-3 inline-flex rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        View plans
      </Link>
    </div>
  )
}
