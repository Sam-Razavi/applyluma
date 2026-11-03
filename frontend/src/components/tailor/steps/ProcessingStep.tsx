import { useEffect, useState } from 'react'
import { TailorTips } from '../TailorTips'

export function ProcessingStep({ wantCv, wantCover }: { wantCv: boolean; wantCover: boolean }) {
  const heading =
    wantCv && wantCover
      ? 'Tailoring your CV and writing your cover letter'
      : wantCv
        ? 'Tailoring your CV'
        : 'Writing your cover letter'

  const [activeStep, setActiveStep] = useState(0)
  const steps = [
    { label: 'Parsing CV', sublabel: 'Extracting your experience' },
    { label: 'Detecting language', sublabel: 'Matching the output language' },
    { label: 'Analysing job description', sublabel: 'Identifying key requirements' },
    { label: 'Generating', sublabel: 'AI is writing your documents' },
    { label: 'Finalising', sublabel: 'Preparing your preview' },
  ]

  useEffect(() => {
    const delays = [2000, 4000, 8000, 20000]
    const timers = delays.map((delay, index) =>
      window.setTimeout(() => setActiveStep(index + 1), delay),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl border border-line bg-surface p-8">
        <h2 className="mb-6 text-base font-semibold text-fg">{heading}</h2>
        <ol className="flex flex-col gap-4 sm:flex-row sm:items-start">
          {steps.map((s, index) => {
            const done = index < activeStep
            const active = index === activeStep
            return (
              <li key={s.label} className="flex min-w-0 items-start gap-3 sm:flex-1">
                <div
                  className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-colors ${
                    done ? 'bg-green-500' : active ? 'animate-pulse bg-brand-500' : 'bg-track'
                  }`}
                >
                  {done && (
                    <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <div>
                  <p className={`text-sm font-medium ${active ? 'text-fg' : 'text-fg-subtle'}`}>{s.label}</p>
                  {active && <p className="mt-0.5 text-xs text-fg-subtle">{s.sublabel}</p>}
                </div>
              </li>
            )
          })}
        </ol>
      </div>
      <TailorTips />
    </div>
  )
}
