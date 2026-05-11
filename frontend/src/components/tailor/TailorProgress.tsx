import { useEffect, useState } from 'react'
import { CheckIcon } from '@heroicons/react/24/outline'

const STEPS = [
  { label: 'Parsing CV', sublabel: 'Extracting your experience' },
  { label: 'Detecting language', sublabel: 'Matching the output language' },
  { label: 'Analysing job description', sublabel: 'Identifying key requirements' },
  { label: 'Rewriting sections', sublabel: 'AI tailoring is in progress' },
  { label: 'Finalising', sublabel: 'Preparing your preview' },
]

export function TailorProgress() {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    const delays = [2000, 4000, 8000, 20000]
    const timers = delays.map((delay, index) =>
      window.setTimeout(() => setActiveStep(index + 1), delay),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8">
      <h2 className="mb-6 text-base font-semibold text-gray-900">Tailoring your CV</h2>
      <ol className="space-y-4">
        {STEPS.map((step, index) => {
          const done = index < activeStep
          const active = index === activeStep
          return (
            <li key={step.label} className="flex items-start gap-3">
              <div
                className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-colors ${
                  done ? 'bg-green-500' : active ? 'animate-pulse bg-brand-500' : 'bg-gray-200'
                }`}
              >
                {done && <CheckIcon className="h-3 w-3 text-white" />}
              </div>
              <div>
                <p
                  className={`text-sm font-medium ${
                    active ? 'text-gray-900' : done ? 'text-gray-500' : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </p>
                {active && <p className="mt-0.5 text-xs text-gray-400">{step.sublabel}</p>}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
