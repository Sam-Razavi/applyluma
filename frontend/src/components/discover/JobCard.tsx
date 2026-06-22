import { BookmarkIcon as BookmarkOutline } from '@heroicons/react/24/outline'
import { BookmarkIcon as BookmarkSolid, MapPinIcon, CurrencyDollarIcon, BriefcaseIcon } from '@heroicons/react/24/solid'
import type { DiscoveredJob } from '../../types/jobDiscovery'
import { SOURCE_LABELS } from '../../types/jobDiscovery'

interface Props {
  job: DiscoveredJob
  onClick: (job: DiscoveredJob) => void
  onSave: (job: DiscoveredJob) => void
}

function ScoreBar({ value, label }: { value: number | null; label: string }) {
  if (value === null) return null
  const pct = Math.round(value)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2 text-xs text-fg-subtle">
      <span className="w-20 shrink-0">{label}</span>
      <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-track">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right font-medium text-fg-muted">{pct}%</span>
    </div>
  )
}

function formatSalary(min: number | null, max: number | null): string | null {
  if (!min && !max) return null
  const fmt = (n: number) =>
    n >= 1000 ? `${Math.round(n / 1000)}k` : String(n)
  if (min && max) return `${fmt(min)}–${fmt(max)} kr`
  if (min) return `from ${fmt(min)} kr`
  return `up to ${fmt(max!)} kr`
}

export default function JobCard({ job, onClick, onSave }: Props) {
  const score = job.match_score !== null ? Math.round(job.match_score) : null
  const salary = formatSalary(job.salary_min, job.salary_max)
  const hasSubScores =
    job.skills_match !== null || job.experience_match !== null || job.salary_match_score !== null

  const scoreColor =
    score === null
      ? 'text-fg-subtle bg-surface'
      : score >= 80
        ? 'text-chip-success-fg bg-chip-success'
        : score >= 60
          ? 'text-chip-warn-fg bg-chip-warn'
          : 'text-chip-danger-fg bg-chip-danger'

  return (
    <div
      className="group relative flex flex-col gap-3 overflow-hidden rounded-2xl border border-line bg-surface p-5 shadow-sm transition-shadow hover:shadow-md cursor-pointer"
      onClick={() => onClick(job)}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-fg group-hover:text-accent-text">
            {job.title}
          </h3>
          <p className="mt-0.5 truncate text-xs text-fg-subtle">{job.company}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {score !== null && (
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${scoreColor}`}>
              {score}%
            </span>
          )}
          {(job.application_id || job.application_status) && (
            <span className="rounded-full bg-chip-success px-2.5 py-0.5 text-xs font-medium text-chip-success-fg">
              {job.application_status ? job.application_status.replace('_', ' ') : 'Applied'}
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onSave(job)
            }}
            className="rounded-lg p-1 text-fg-subtle transition-colors hover:text-accent-text focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label={job.is_saved ? 'Unsave job' : 'Save job'}
          >
            {job.is_saved ? (
              <BookmarkSolid className="h-5 w-5 text-accent-text" />
            ) : (
              <BookmarkOutline className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 text-xs text-fg-subtle">
        {job.location && (
          <span className="flex items-center gap-1">
            <MapPinIcon className="h-3.5 w-3.5" />
            {job.location}
          </span>
        )}
        {salary && (
          <span className="flex items-center gap-1">
            <CurrencyDollarIcon className="h-3.5 w-3.5" />
            {salary}
          </span>
        )}
        {job.employment_type && (
          <span className="flex items-center gap-1">
            <BriefcaseIcon className="h-3.5 w-3.5" />
            {job.employment_type.replace('_', ' ')}
          </span>
        )}
        {job.remote_allowed && (
          <span className="rounded-full bg-chip-accent px-2 py-0.5 text-accent-text">Remote</span>
        )}
        <span className="ml-auto text-fg-subtle">{SOURCE_LABELS[job.source] ?? job.source}</span>
      </div>

      {/* Score bars — only render when sub-scores exist */}
      {job.match_score !== null && hasSubScores && (
        <div className="space-y-1 border-t border-line pt-3">
          <ScoreBar value={job.skills_match} label="Skills" />
          <ScoreBar value={job.experience_match} label="Experience" />
          <ScoreBar value={job.salary_match_score} label="Salary" />
        </div>
      )}

      {/* Explanation snippet */}
      {job.explanation && (
        <p className="text-xs text-fg-subtle line-clamp-1">{job.explanation}</p>
      )}
    </div>
  )
}
