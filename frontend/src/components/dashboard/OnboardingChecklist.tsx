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
    <div className="rounded-2xl border border-primary-600/30 bg-gradient-to-br from-primary-900/20 to-white/[0.04] p-5 ">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-white/90 ">
            Get started — {completedCount} of 3 done
          </h2>
          <p className="mt-0.5 text-xs text-white/30 ">
            Complete these steps to get the most out of ApplyLuma.
          </p>
        </div>
        <div className="flex shrink-0 gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`h-1.5 w-8 rounded-full transition-colors ${
                i < completedCount ? 'bg-brand-500' : 'bg-white/[0.06] '
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
                  ? 'border-[rgba(52,195,143,0.22)] bg-[rgba(52,195,143,0.14)] opacity-70 '
                  : isNext
                  ? 'border-primary-600/30 bg-white/[0.04] shadow-sm '
                  : 'border-white/10 bg-white/[0.04] '
              }`}
            >
              {/* Step indicator */}
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-500" />
                ) : (
                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                      isNext
                        ? 'bg-brand-600 text-white'
                        : 'bg-white/[0.06] text-white/30 '
                    }`}
                  >
                    {step.number}
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-semibold ${isDone ? 'text-white/30 line-through' : 'text-white/90 '}`}>
                  {step.title}
                </p>
                {!isDone && (
                  <p className="mt-0.5 text-xs text-white/30 ">
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
                      : 'bg-white/[0.04] text-white/55 hover:bg-white/[0.08] '
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
