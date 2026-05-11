import type { TailorIntensity } from '../../types/tailor'

const OPTIONS: { value: TailorIntensity; label: string; description: string }[] = [
  {
    value: 'light',
    label: 'Light',
    description: 'Fix keyword gaps and tighten bullets. Structure stays familiar.',
  },
  {
    value: 'medium',
    label: 'Medium',
    description: 'Rewrite bullets, refresh the summary, and promote relevant sections.',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    description: 'Fully optimize the CV for the target role and remove weak sections.',
  },
]

interface Props {
  value: TailorIntensity
  onChange: (value: TailorIntensity) => void
}

export function IntensitySelector({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`min-h-[112px] rounded-xl border-2 p-4 text-left transition-colors ${
            value === option.value
              ? 'border-brand-500 bg-brand-50'
              : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
        >
          <p className="text-sm font-semibold text-gray-900">{option.label}</p>
          <p className="mt-1 text-xs leading-5 text-gray-500">{option.description}</p>
        </button>
      ))}
    </div>
  )
}
