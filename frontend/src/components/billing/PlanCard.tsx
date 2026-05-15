import { CheckIcon } from '@heroicons/react/24/outline'

interface Props {
  name: string
  price: string
  description: string
  features: string[]
  ctaLabel: string
  highlighted?: boolean
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
}

export default function PlanCard({
  name,
  price,
  description,
  features,
  ctaLabel,
  highlighted,
  disabled,
  loading,
  onClick,
}: Props) {
  return (
    <section
      className={`flex h-full w-full flex-col rounded-2xl border bg-white p-6 shadow-sm md:flex-1 ${
        highlighted ? 'border-brand-300 ring-2 ring-brand-100' : 'border-gray-200'
      }`}
    >
      <div>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">{name}</h2>
          {highlighted && (
            <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700">
              Popular
            </span>
          )}
        </div>
        <p className="mt-2 text-sm text-gray-500">{description}</p>
        <p className="mt-6 text-3xl font-bold text-gray-900">{price}</p>
      </div>

      <ul className="mt-6 flex-1 space-y-3">
        {features.map((feature) => (
          <li key={feature} className="flex gap-2 text-sm text-gray-600">
            <CheckIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onClick}
        disabled={disabled || loading}
        className={`mt-6 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
          highlighted
            ? 'bg-brand-600 text-white hover:bg-brand-700'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
      >
        {loading ? 'Opening...' : ctaLabel}
      </button>
    </section>
  )
}
