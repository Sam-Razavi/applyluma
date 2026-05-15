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
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <span className="w-20 shrink-0">{label}</span>
      <div className="h-1.5 flex-1 rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right font-medium text-gray-700">{pct}%</span>
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

  const scoreColor =
    score === null
      ? 'text-gray-400 bg-gray-100'
      : score >= 80
        ? 'text-green-700 bg-green-100'
        : score >= 60
          ? 'text-yellow-700 bg-yellow-100'
          : 'text-red-700 bg-red-100'

  return (
    <div
      className="group relative flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md cursor-pointer"
      onClick={() => onClick(job)}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-gray-900 group-hover:text-primary-700">
            {job.title}
          </h3>
          <p className="mt-0.5 truncate text-xs text-gray-500">{job.company}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {score !== null && (
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${scoreColor}`}>
              {score}%
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onSave(job)
            }}
            className="rounded-lg p-1 text-gray-400 transition-colors hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label={job.is_saved ? 'Unsave job' : 'Save job'}
          >
            {job.is_saved ? (
              <BookmarkSolid className="h-5 w-5 text-primary-600" />
            ) : (
              <BookmarkOutline className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
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
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-700">Remote</span>
        )}
        <span className="ml-auto text-gray-400">{SOURCE_LABELS[job.source] ?? job.source}</span>
      </div>

      {/* Score bars */}
      {job.match_score !== null && (
        <div className="space-y-1 border-t border-gray-100 pt-3">
          <ScoreBar value={job.skills_match} label="Skills" />
          <ScoreBar value={job.experience_match} label="Experience" />
          <ScoreBar value={job.salary_match_score} label="Salary" />
        </div>
      )}

      {/* Explanation snippet */}
      {job.explanation && (
        <p className="text-xs text-gray-500 line-clamp-1">{job.explanation}</p>
      )}
    </div>
  )
}
