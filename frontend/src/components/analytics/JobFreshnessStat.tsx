import { useEffect, useState } from 'react'
import { BoltIcon } from '@heroicons/react/24/solid'
import { analyticsApi } from '../../services/api'
import type { JobFreshness } from '../../types'

function relativeTime(iso: string | null): string {
  if (!iso) return 'unknown'
  const diffMs = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diffMs / 60000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const days = Math.floor(hr / 24)
  return `${days}d ago`
}

// Live "the app is working" stat sourced from raw_job_postings (no dbt dependency).
// Self-fetching so it can drop into the Dashboard and the Analytics header alike.
export default function JobFreshnessStat({ className = '' }: { className?: string }) {
  const [data, setData] = useState<JobFreshness | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    analyticsApi
      .freshness()
      .then((res) => {
        if (active) setData(res)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) return null

  if (!data) {
    return (
      <div
        className={`h-[58px] animate-pulse rounded-xl border border-line bg-surface ${className}`}
        aria-hidden
      />
    )
  }

  const headline =
    data.new_today > 0
      ? `${data.new_today.toLocaleString()} new ${data.new_today === 1 ? 'job' : 'jobs'} today`
      : `${data.total_jobs.toLocaleString()} jobs tracked`

  return (
    <div
      className={`flex items-center gap-3 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-3 ${className}`}
      role="status"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-chip-accent">
        <BoltIcon className="h-5 w-5 text-accent-text" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-fg">{headline}</p>
        <p className="truncate text-xs text-fg-subtle">
          {data.total_jobs.toLocaleString()} total · {data.new_this_week.toLocaleString()} this week ·
          updated {relativeTime(data.last_updated)}
        </p>
      </div>
    </div>
  )
}
