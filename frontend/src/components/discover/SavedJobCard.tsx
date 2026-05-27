import { MapPinIcon, PlusCircleIcon, StarIcon, TrashIcon } from '@heroicons/react/24/outline'
import { StarIcon as StarSolid } from '@heroicons/react/24/solid'
import type { SavedJob } from '../../types/jobDiscovery'

interface Props {
  saved: SavedJob
  onClick: (jobId: string) => void
  onStar: (savedId: string, starred: boolean) => void
  onDelete: (savedId: string) => void
  onAddToDescriptions?: (saved: SavedJob) => void
  addingToDescriptions?: boolean
}

function formatSalary(min: number | null | undefined, max: number | null | undefined): string | null {
  if (!min && !max) return null
  const fmt = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(n))
  if (min && max) return `${fmt(min)}–${fmt(max)} kr`
  if (min) return `from ${fmt(min)} kr`
  return `up to ${fmt(max!)} kr`
}

export default function SavedJobCard({
  saved,
  onClick,
  onStar,
  onDelete,
  onAddToDescriptions,
  addingToDescriptions = false,
}: Props) {
  const job = saved.job
  const salary = job ? formatSalary(job.salary_min, job.salary_max) : null

  return (
    <div
      className="group relative flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md cursor-pointer"
      onClick={() => onClick(saved.raw_job_posting_id)}
      data-testid="saved-job-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-gray-900 group-hover:text-primary-700">
            {job?.title ?? 'Unknown job'}
          </h3>
          {job?.company && (
            <p className="mt-0.5 truncate text-xs text-gray-500">{job.company}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {onAddToDescriptions && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onAddToDescriptions(saved)
              }}
              disabled={addingToDescriptions}
              className="rounded-lg p-1 text-gray-400 transition-colors hover:text-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-40"
              aria-label="Add to job descriptions"
              title="Add to Job Descriptions"
            >
              {addingToDescriptions ? (
                <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
                </svg>
              ) : (
                <PlusCircleIcon className="h-5 w-5" />
              )}
            </button>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onStar(saved.id, !saved.starred)
            }}
            className="rounded-lg p-1 text-gray-400 transition-colors hover:text-yellow-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label={saved.starred ? 'Unstar job' : 'Star job'}
          >
            {saved.starred ? (
              <StarSolid className="h-5 w-5 text-yellow-400" />
            ) : (
              <StarIcon className="h-5 w-5" />
            )}
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(saved.id)
            }}
            className="rounded-lg p-1 text-gray-400 transition-colors hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-red-500"
            aria-label="Remove saved job"
          >
            <TrashIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Meta */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        {job?.location && (
          <span className="flex items-center gap-1">
            <MapPinIcon className="h-3.5 w-3.5" />
            {job.location}
          </span>
        )}
        {salary && <span>{salary}</span>}
        {job?.remote_allowed && (
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-700">Remote</span>
        )}
        {job?.employment_type && (
          <span>{job.employment_type.replace('_', ' ')}</span>
        )}
        {saved.list_name && (
          <span className="ml-auto rounded-full bg-primary-50 px-2 py-0.5 text-primary-700">
            {saved.list_name}
          </span>
        )}
      </div>

      {/* Notes */}
      {saved.notes && (
        <p className="text-xs text-gray-500 line-clamp-2 border-t border-gray-100 pt-2">
          {saved.notes}
        </p>
      )}
    </div>
  )
}
