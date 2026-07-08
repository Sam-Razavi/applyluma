import { useEffect, useState } from 'react'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid'
import { cvApi } from '../../services/api'
import type { CVCompleteness } from '../../types'

function barColor(score: number): string {
  if (score >= 80) return 'bg-chip-success-fg'
  if (score >= 50) return 'bg-chip-warn-fg'
  return 'bg-chip-danger-fg'
}

export function CompletenessBar({ score, onClick }: { score: number; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title="CV completeness — click for details"
      className="mt-1 flex items-center gap-2 group"
      aria-label={`CV completeness ${score}%`}
    >
      <span className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-strong">
        <span
          className={`block h-full rounded-full ${barColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </span>
      <span className="text-xs text-fg-subtle group-hover:text-fg-muted">{score}%</span>
    </button>
  )
}

export function CompletenessChecklist({ cvId }: { cvId: string }) {
  const [data, setData] = useState<CVCompleteness | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    cvApi
      .completeness(cvId)
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => {
      cancelled = true
    }
  }, [cvId])

  if (error) {
    return <p className="text-xs text-fg-subtle">Could not load the completeness checklist.</p>
  }
  if (!data) {
    return <p className="text-xs text-fg-subtle">Loading checklist…</p>
  }

  return (
    <ul className="space-y-1.5">
      {data.checks.map((check) => (
        <li key={check.id} className="flex items-start gap-2 text-xs">
          {check.passed ? (
            <CheckCircleIcon className="h-4 w-4 flex-shrink-0 text-chip-success-fg" />
          ) : (
            <XCircleIcon className="h-4 w-4 flex-shrink-0 text-chip-danger-fg" />
          )}
          <span className={check.passed ? 'text-fg-muted' : 'text-fg'}>
            <span className="font-medium">{check.label}</span>
            {!check.passed && <span className="block text-fg-subtle">{check.hint}</span>}
          </span>
        </li>
      ))}
    </ul>
  )
}
