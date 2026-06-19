import {
  ArrowTopRightOnSquareIcon,
  BriefcaseIcon,
  MapPinIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import type { ApplicationCreate } from '../../types/application'
import type { AdzunaJobResult } from '../../services/jobSearchApi'

interface Props {
  job: AdzunaJobResult
  onTrack: (data: Partial<ApplicationCreate>) => void
}

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return 'Salary not listed'
  const formatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
  if (min && max) return `${formatter.format(min)} - ${formatter.format(max)}`
  if (min) return `From ${formatter.format(min)}`
  return `Up to ${formatter.format(max ?? 0)}`
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

export default function JobResultCard({ job, onTrack }: Props) {
  const description = stripHtml(job.description)

  const sourceName = job.source === 'platsbanken' ? 'Platsbanken' : 'Adzuna'

  function handleTrack() {
    onTrack({
      company_name: job.company_name,
      job_title: job.title,
      job_url: job.redirect_url,
      status: 'wishlist',
      source: job.source ?? 'adzuna',
      salary_min: job.salary_min,
      salary_max: job.salary_max,
      location: job.location || null,
      priority: 1,
      notes: description ? `From ${sourceName}:\n\n${description.slice(0, 1200)}` : null,
    })
  }

  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-sm transition hover:border-primary-600/40 hover:shadow-md">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-primary-900/20">
          <BriefcaseIcon className="h-6 w-6 text-primary-400" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-white/90">{job.title}</h2>
          <p className="mt-0.5 text-sm text-white/30">{job.company_name}</p>
        </div>
        {job.redirect_url && (
          <a
            href={job.redirect_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-white/30 transition hover:bg-white/[0.06] hover:text-white/55"
            aria-label="Open job"
          >
            <ArrowTopRightOnSquareIcon className="h-4 w-4" />
          </a>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        {job.location && (
          <span className="inline-flex items-center gap-1 rounded-full bg-white/[0.04] px-2.5 py-1 font-medium text-white/55">
            <MapPinIcon className="h-3.5 w-3.5" />
            {job.location}
          </span>
        )}
        <span className="rounded-full bg-[rgba(52,195,143,0.14)] px-2.5 py-1 font-medium text-emerald-300">
          {formatSalary(job.salary_min, job.salary_max)}
        </span>
        {job.contract_type && (
          <span className="rounded-full bg-[rgba(8,145,178,0.15)] px-2.5 py-1 font-medium text-cyan-300">
            {job.contract_type}
          </span>
        )}
        {job.source && (
          <span className="rounded-full bg-[rgba(139,92,246,0.15)] px-2.5 py-1 font-medium text-violet-300">
            {sourceName}
          </span>
        )}
      </div>

      {description && (
        <p className="mt-4 line-clamp-3 text-sm leading-6 text-white/55">
          {description.slice(0, 320)}
          {description.length > 320 ? '...' : ''}
        </p>
      )}

      <div className="mt-5 flex justify-end">
        <button
          type="button"
          onClick={handleTrack}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          <PlusIcon className="h-4 w-4" />
          Track This Job
        </button>
      </div>
    </article>
  )
}
