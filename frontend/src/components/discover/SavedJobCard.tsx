import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BriefcaseIcon, MapPinIcon, SparklesIcon, StarIcon, TrashIcon } from '@heroicons/react/24/outline'
import { StarIcon as StarSolid } from '@heroicons/react/24/solid'
import type { SavedJob } from '../../types/jobDiscovery'
import { useUsageStore, usageHint } from '../../stores/usage'

interface Props {
  saved: SavedJob
  onClick: (jobId: string) => void
  onStar: (savedId: string, starred: boolean) => void
  onDelete: (savedId: string) => void
  onAddToApplications?: (saved: SavedJob) => void
  addingToApplications?: boolean
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
  onAddToApplications,
  addingToApplications = false,
}: Props) {
  const navigate = useNavigate()
  const job = saved.job
  const salary = job ? formatSalary(job.salary_min, job.salary_max) : null
  const tailorUsage = useUsageStore((s) => s.tailorUsage)
  const coverUsage = useUsageStore((s) => s.coverUsage)
  const loadUsage = useUsageStore((s) => s.loadUsage)
  const limitHint = usageHint(tailorUsage, coverUsage)

  useEffect(() => {
    void loadUsage()
  }, [loadUsage])

  return (
    <div
      className="group relative flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5 shadow-sm transition-shadow hover:shadow-md cursor-pointer"
      onClick={() => onClick(saved.raw_job_posting_id)}
      data-testid="saved-job-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-fg group-hover:text-accent-text">
            {job?.title ?? 'Unknown job'}
          </h3>
          {job?.company && (
            <p className="mt-0.5 truncate text-xs text-fg-subtle">{job.company}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onStar(saved.id, !saved.starred)
            }}
            className="-m-1 rounded-lg p-2 text-fg-subtle transition-colors hover:text-chip-warn-fg focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label={saved.starred ? 'Unstar job' : 'Star job'}
          >
            {saved.starred ? (
              <StarSolid className="h-5 w-5 text-chip-warn-fg" />
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
            className="-m-1 rounded-lg p-2 text-fg-subtle transition-colors hover:text-chip-danger-fg focus:outline-none focus:ring-2 focus:ring-red-500"
            aria-label="Remove saved job"
          >
            <TrashIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Meta */}
      <div className="flex flex-wrap gap-3 text-xs text-fg-subtle">
        {job?.location && (
          <span className="flex items-center gap-1">
            <MapPinIcon className="h-3.5 w-3.5" />
            {job.location}
          </span>
        )}
        {salary && <span>{salary}</span>}
        {job?.remote_allowed && (
          <span className="rounded-full bg-chip-accent px-2 py-0.5 text-accent-text">Remote</span>
        )}
        {job?.employment_type && (
          <span>{job.employment_type.replace('_', ' ')}</span>
        )}
        {saved.list_name && (
          <span className="ml-auto rounded-full bg-primary-900/20 px-2 py-0.5 text-accent-text">
            {saved.list_name}
          </span>
        )}
        {job?.application_status && (
          <span className="rounded-full bg-chip-success px-2 py-0.5 text-xs font-medium text-chip-success-fg">
            {job.application_status.replace('_', ' ')}
          </span>
        )}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2 border-t border-line pt-2">
        {!job?.application_status && onAddToApplications && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onAddToApplications(saved)
            }}
            disabled={addingToApplications}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-fg-muted transition-colors hover:bg-surface-strong hover:text-fg disabled:opacity-40"
          >
            <BriefcaseIcon className="h-3.5 w-3.5" />
            {addingToApplications ? 'Adding...' : 'Add to Applications'}
          </button>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            navigate('/ai-tailor', {
              state: {
                rawJobPostingId: saved.raw_job_posting_id,
                jobTitle: job?.title,
                company: job?.company,
              },
            })
          }}
          className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-fg-muted transition-colors hover:bg-surface-strong hover:text-fg"
        >
          <SparklesIcon className="h-3.5 w-3.5" />
          <span className="sm:hidden">Tailor CV</span>
          <span className="hidden sm:inline">Tailor CV + Cover Letter</span>
        </button>
      </div>

      {/* Daily-limit hint */}
      {limitHint && <p className="text-xs text-chip-danger-fg">{limitHint}</p>}

      {/* Notes */}
      {saved.notes && (
        <p className="text-xs text-fg-subtle line-clamp-2 border-t border-line pt-2">
          {saved.notes}
        </p>
      )}
    </div>
  )
}
