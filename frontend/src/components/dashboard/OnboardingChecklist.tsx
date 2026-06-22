import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircleIcon } from '@heroicons/react/24/solid'
import { ArrowRightIcon } from '@heroicons/react/24/outline'
import { tailorApi } from '../../services/tailorApi'

interface Props {
  hasCv: boolean
  hasJd: boolean
  loading: boolean
}

const STEPS = [
  {
    key: 'cv' as const,
    number: 1,
    title: 'Upload your CV',
    description: 'Add a PDF or Word document so ApplyLuma can analyse and tailor it.',
    cta: 'Upload CV',
    href: '/cvs',
  },
  {
    key: 'jd' as const,
    number: 2,
    title: 'Add a job description',
    description: 'Paste a job URL or add it manually — we extract the keywords automatically.',
    cta: 'Add job',
    href: '/jobs?tab=descriptions',
  },
  {
    key: 'tailor' as const,
    number: 3,
    title: 'Tailor your CV with AI',
    description: 'Match your CV to the job and get a tailored version in under a minute.',
    cta: 'Tailor now',
    href: '/ai-tailor',
  },
]

export default function OnboardingChecklist({ hasCv, hasJd, loading }: Props) {
  const [hasTailored, setHasTailored] = useState(false)
  const [tailorLoading, setTailorLoading] = useState(true)

  useEffect(() => {
    tailorApi
      .getHistory()
      .then((jobs) => setHasTailored(jobs.length > 0))
      .catch(() => setHasTailored(false))
      .finally(() => setTailorLoading(false))
  }, [])

  const done = { cv: hasCv, jd: hasJd, tailor: hasTailored }
  const allLoading = loading || tailorLoading
  const allDone = done.cv && done.jd && done.tailor
  const completedCount = [done.cv, done.jd, done.tailor].filter(Boolean).length

  if (allLoading || allDone) return null

  return (
    <div className="rounded-2xl border border-accent-muted bg-gradient-to-br from-accent-muted to-surface p-5 ">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-fg ">
            Get started — {completedCount} of 3 done
          </h2>
          <p className="mt-0.5 text-xs text-fg-subtle ">
            Complete these steps to get the most out of ApplyLuma.
          </p>
        </div>
        <div className="flex shrink-0 gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`h-1.5 w-8 rounded-full transition-colors ${
                i < completedCount ? 'bg-accent' : 'bg-track '
              }`}
            />
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {STEPS.map((step) => {
          const isDone = done[step.key]
          const isNext = !isDone && STEPS.filter((s) => !done[s.key])[0]?.key === step.key
          return (
            <div
              key={step.key}
              className={`flex items-start gap-3 rounded-xl border p-4 transition-all ${
                isDone
                  ? 'border-chip-success bg-chip-success opacity-70 '
                  : isNext
                  ? 'border-accent-muted bg-surface shadow-sm '
                  : 'border-line bg-surface '
              }`}
            >
              {/* Step indicator */}
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircleIcon className="h-5 w-5 text-chip-success-fg" />
                ) : (
                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                      isNext
                        ? 'bg-brand-600 text-white'
                        : 'bg-track text-fg-subtle '
                    }`}
                  >
                    {step.number}
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-semibold ${isDone ? 'text-fg-subtle line-through' : 'text-fg '}`}>
                  {step.title}
                </p>
                {!isDone && (
                  <p className="mt-0.5 text-xs text-fg-subtle ">
                    {step.description}
                  </p>
                )}
              </div>

              {/* CTA */}
              {!isDone && (
                <Link
                  to={step.href}
                  className={`shrink-0 self-center rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    isNext
                      ? 'bg-brand-600 text-white hover:bg-brand-700'
                      : 'bg-track text-fg-muted hover:bg-surface-strong '
                  }`}
                >
                  <span className="flex items-center gap-1">
                    {step.cta}
                    {isNext && <ArrowRightIcon className="h-3 w-3" />}
                  </span>
                </Link>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
