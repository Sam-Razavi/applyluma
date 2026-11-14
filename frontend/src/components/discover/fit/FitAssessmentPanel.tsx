import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowPathIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { getErrorMessage } from '../../../lib/errors'
import { fitAssessmentApi } from '../../../services/fitAssessmentApi'
import type {
  FitAssessment,
  FitImportance,
  FitRecommendation,
  FitRequirement,
  FitStatus,
} from '../../../types/fitAssessment'

interface Props {
  jobId: string
}

const POLL_MS = 2000

const RECOMMENDATION: Record<FitRecommendation, { label: string; className: string }> = {
  high_priority: { label: 'High priority', className: 'bg-success-500/15 text-success-600' },
  consider: { label: 'Consider', className: 'bg-warning-500/15 text-warning-600' },
  low_priority: { label: 'Low priority', className: 'bg-danger-500/15 text-danger-600' },
}

const STATUS: Record<FitStatus, { label: string; className: string }> = {
  met: { label: 'Met', className: 'bg-success-500/15 text-success-600' },
  partly_met: { label: 'Partly met', className: 'bg-warning-500/15 text-warning-600' },
  not_met: { label: 'Not met', className: 'bg-danger-500/15 text-danger-600' },
  not_enough_information: { label: 'Not enough information', className: 'bg-surface-strong text-fg-muted' },
}

// Sized like the other actions in the job detail (Save, Tailor CV).
const ACTION =
  'flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm disabled:opacity-60 sm:w-auto'

const GROUPS: { importance: FitImportance; title: string; hint: string }[] = [
  { importance: 'mandatory', title: 'Mandatory', hint: 'These decide the recommendation.' },
  { importance: 'preferred', title: 'Preferred', hint: 'Shown for your information.' },
  {
    importance: 'unclear',
    title: 'Not stated as required or preferred',
    hint: 'The ad lists these without saying how much they matter.',
  },
]

function Requirement({ item }: { item: FitRequirement }) {
  const status = STATUS[item.status]
  return (
    <li className="rounded-lg border border-line bg-surface p-3">
      {/* A short chip stays on the right; a long one drops under the title on a
          phone instead of squeezing it into a narrow column. */}
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1.5">
        <span className="min-w-[55%] flex-1 text-sm font-medium text-fg">{item.text}</span>
        <span
          className={`shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ${status.className}`}
        >
          {status.label}
        </span>
      </div>
      {item.note && <p className="mt-1 text-xs text-fg-muted">{item.note}</p>}
      {item.cv_quote && item.cv_quote_found && (
        <p className="mt-2 border-l-2 border-line-strong pl-2 text-xs italic text-fg-muted">
          From your CV: “{item.cv_quote}”
        </p>
      )}
      {item.downgraded && (
        <p className="mt-2 text-xs text-warning-600">
          The evidence given for this could not be found in your CV, so it is not counted as met.
        </p>
      )}
      {item.ad_quote && (
        <p className="mt-1 text-xs text-fg-subtle">
          From the ad: “{item.ad_quote}”{!item.ad_quote_found && ' (wording not found in the ad)'}
        </p>
      )}
    </li>
  )
}

export default function FitAssessmentPanel({ jobId }: Props) {
  const [enabled, setEnabled] = useState(false)
  const [assessment, setAssessment] = useState<FitAssessment | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(true)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true
    setAssessment(null)
    setError(null)
    void fitAssessmentApi
      .status()
      .then(async (s) => {
        if (!active || !s.enabled) return
        setEnabled(true)
        // A stored assessment is shown again without a new model call.
        const latest = await fitAssessmentApi.latest(jobId)
        if (active) setAssessment(latest)
      })
      .catch(() => {
        // The panel is an extra: if its status cannot be read, it stays hidden.
      })
    return () => {
      active = false
    }
  }, [jobId])

  const running = assessment?.status === 'pending' || assessment?.status === 'processing'

  useEffect(() => {
    if (!running || !assessment) return
    timer.current = setTimeout(() => {
      void fitAssessmentApi
        .get(assessment.id)
        .then(setAssessment)
        .catch((err: unknown) => setError(getErrorMessage(err, 'Could not read the assessment')))
    }, POLL_MS)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [running, assessment])

  const run = useCallback(
    async (force: boolean) => {
      setBusy(true)
      setError(null)
      try {
        setAssessment(await fitAssessmentApi.request(jobId, force))
      } catch (err) {
        setError(getErrorMessage(err, 'Could not start the assessment'))
      } finally {
        setBusy(false)
      }
    },
    [jobId],
  )

  if (!enabled) return null

  const result = assessment?.status === 'complete' ? assessment.result : null

  return (
    <section className="rounded-xl border border-line bg-surface-raised p-4" aria-label="AI assessment">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-fg">
          <SparklesIcon className="h-4 w-4 text-accent-text" aria-hidden="true" />
          AI assessment
          {result && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${RECOMMENDATION[result.recommendation].className}`}
            >
              {RECOMMENDATION[result.recommendation].label}
            </span>
          )}
        </span>
        <ChevronDownIcon
          className={`h-4 w-4 shrink-0 text-fg-subtle transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          <p className="text-xs text-fg-muted">
            Reads this job ad and your default CV, and nothing else. It lists what the ad requires, what
            your CV shows for each requirement, and what is missing. It can be wrong: check the quoted
            evidence.
          </p>

          {error && (
            <p role="alert" className="text-sm text-danger-600">
              {error}
            </p>
          )}

          {!assessment && (
            <button
              type="button"
              className={`btn-primary ${ACTION}`}
              onClick={() => void run(false)}
              disabled={busy}
            >
              <SparklesIcon className="h-4 w-4" aria-hidden="true" />
              {busy ? 'Starting…' : 'Assess this job'}
            </button>
          )}

          {running && (
            <p className="flex items-center gap-3 text-sm text-fg-muted" role="status">
              <span
                className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary-500 border-t-transparent"
                aria-hidden="true"
              />
              Reading the ad and your CV. This takes up to half a minute.
            </p>
          )}

          {assessment?.status === 'failed' && (
            <div className="space-y-2">
              <p className="text-sm text-danger-600">
                The assessment could not be completed{assessment.error_message ? `: ${assessment.error_message}` : '.'}
              </p>
              <button
                type="button"
                className={`btn-ghost ${ACTION}`}
                onClick={() => void run(true)}
                disabled={busy}
              >
                <ArrowPathIcon className="h-4 w-4" aria-hidden="true" />
                Try again
              </button>
            </div>
          )}

          {result && (
            <>
              <div>
                <p className="text-sm font-medium text-fg">{result.reason}</p>
                {result.summary && <p className="mt-1 text-sm text-fg-muted">{result.summary}</p>}
              </div>

              {result.limited_information && (
                <p className="flex items-start gap-2 rounded-lg bg-warning-500/10 p-3 text-xs text-warning-600">
                  <ExclamationTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  Limited information: too little could be judged from the ad and your CV for a firm
                  recommendation.
                </p>
              )}

              {GROUPS.map(({ importance, title, hint }) => {
                const items = result.requirements.filter((r) => r.importance === importance)
                if (items.length === 0) return null
                return (
                  <div key={importance}>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                      {title} ({items.length})
                    </h4>
                    <p className="mb-2 text-xs text-fg-subtle">{hint}</p>
                    <ul className="space-y-2">
                      {items.map((item) => (
                        <Requirement key={item.id} item={item} />
                      ))}
                    </ul>
                  </div>
                )
              })}

              {result.missing_information.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                    Missing or unclear information
                  </h4>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-fg-muted">
                    {result.missing_information.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-xs text-fg-muted">This is a recommendation. The decision is yours.</p>

              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                <span className="text-xs text-fg-subtle">
                  Rule {result.rule} · rules v{assessment?.rules_version} · prompt v{assessment?.prompt_version}
                </span>
                <button
                  type="button"
                  className="btn-ghost flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs disabled:opacity-60"
                  onClick={() => void run(true)}
                  disabled={busy}
                >
                  <ArrowPathIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  {busy ? 'Starting…' : 'Run again'}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  )
}
