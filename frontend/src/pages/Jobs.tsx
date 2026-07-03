import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  BookmarkIcon,
  BriefcaseIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ExclamationCircleIcon,
  LinkIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarSolid } from '@heroicons/react/24/solid'
import { StarIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import type { AxiosError } from 'axios'
import JobDetail from '../components/discover/JobDetail'
import { jobApi } from '../services/api'
import type { CreateJobDescriptionRequest } from '../services/api'
import type { JobDescription } from '../types'

const jobSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  job_title: z.string().min(1, 'Job title is required'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  url: z.string().url('Enter a valid URL').optional().or(z.literal('')),
})
type JobFormData = z.infer<typeof jobSchema>

const KEYWORD_COLORS = [
  'bg-chip-accent text-accent-text',
  'bg-chip-accent text-accent-text',
  'bg-chip-success text-chip-success-fg',
  'bg-chip-warn text-chip-warn-fg',
  'bg-chip-accent text-pink-700',
  'bg-cyan-100 text-cyan-700',
  'bg-chip-warn text-chip-warn-fg',
]

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function JdSkeleton() {
  return (
    <div className="bg-track rounded-2xl border border-line p-5 space-y-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-surface rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-4 bg-surface rounded w-1/3" />
          <div className="h-3 bg-surface rounded w-1/4" />
        </div>
      </div>
      <div className="flex gap-2">
        {[...Array(4)].map((_, i) => <div key={i} className="h-5 w-16 bg-surface rounded-full" />)}
      </div>
    </div>
  )
}

export default function Jobs() {
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'alpha'>('date')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailJobId, setDetailJobId] = useState<string | null>(null)

  const [addOpen, setAddOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<JobDescription | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [urlBarOpen, setUrlBarOpen] = useState(false)
  const [scrapeUrlValue, setScrapeUrlValue] = useState('')
  const [scraping, setScraping] = useState(false)

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<JobFormData>({
    resolver: zodResolver(jobSchema),
  })

  useEffect(() => {
    document.title = 'My Jobs | ApplyLuma'
    jobApi
      .list()
      .then(setJobs)
      .catch(() => toast.error('Failed to load jobs'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let result = jobs

    const q = search.trim().toLowerCase()
    if (q) {
      result = result.filter((j) =>
        (j.company_name ?? '').toLowerCase().includes(q) ||
        (j.job_title ?? '').toLowerCase().includes(q),
      )
    }

    return [...result].sort((a, b) => {
      if (a.starred !== b.starred) return a.starred ? -1 : 1
      if (sortBy === 'alpha') {
        return (a.job_title ?? '').toLowerCase().localeCompare((b.job_title ?? '').toLowerCase())
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  }, [jobs, search, sortBy])

  function handleCardClick(job: JobDescription) {
    if (job.source_raw_job_posting_id) {
      setDetailJobId(job.source_raw_job_posting_id)
    } else {
      setExpandedId(expandedId === job.id ? null : job.id)
    }
  }

  async function handleStar(jdId: string, starred: boolean) {
    setJobs((prev) => prev.map((j) => (j.id === jdId ? { ...j, starred } : j)))
    try {
      await jobApi.update(jdId, { starred })
    } catch {
      setJobs((prev) => prev.map((j) => (j.id === jdId ? { ...j, starred: !starred } : j)))
      toast.error('Failed to update')
    }
  }

  async function handleScrapeUrl(e: React.FormEvent) {
    e.preventDefault()
    if (!scrapeUrlValue) return
    setScraping(true)
    try {
      const result = await jobApi.scrapeUrl(scrapeUrlValue)
      reset()
      setValue('company_name', result.company_name)
      setValue('job_title', result.job_title)
      setValue('description', result.description)
      setValue('url', result.url)
      setUrlBarOpen(false)
      setScrapeUrlValue('')
      setAddOpen(true)
    } catch (err) {
      const detail = (err as AxiosError<{ detail?: unknown }>)?.response?.data?.detail
      toast.error(
        typeof detail === 'string' && detail
          ? detail
          : 'Could not extract job details from that URL',
      )
    } finally {
      setScraping(false)
    }
  }

  async function onSubmit(data: JobFormData) {
    setSubmitting(true)
    try {
      const payload: CreateJobDescriptionRequest = {
        company_name: data.company_name,
        job_title: data.job_title,
        description: data.description,
        ...(data.url ? { url: data.url } : {}),
      }
      const jd = await jobApi.create(payload)
      setJobs((prev) => [jd, ...prev])
      toast.success('Job added & keywords extracted!')
      setAddOpen(false)
      reset()
    } catch {
      toast.error('Failed to save job')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await jobApi.remove(deleteTarget.id)
      setJobs((prev) => prev.filter((j) => j.id !== deleteTarget.id))
      toast.success('Job deleted')
      setDeleteTarget(null)
    } catch {
      toast.error('Could not delete job')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-fg">My Jobs</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Your saved jobs and job descriptions — all ready for AI tailoring.
          </p>
        </div>
        <div className="flex flex-col gap-2 self-start sm:self-auto">
          <div className="flex gap-2">
            <button
              onClick={() => { setUrlBarOpen((o) => !o); setScrapeUrlValue('') }}
              className="inline-flex items-center gap-2 bg-surface hover:bg-surface-strong text-fg-muted text-sm font-semibold px-4 py-2.5 rounded-xl border border-line transition-colors"
            >
              <LinkIcon className="h-4 w-4" />
              Import from URL
            </button>
            <button
              onClick={() => { reset(); setAddOpen(true) }}
              className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Manually
            </button>
          </div>
          {urlBarOpen && (
            <form onSubmit={handleScrapeUrl} className="flex gap-2">
              <input
                type="url"
                value={scrapeUrlValue}
                onChange={(e) => setScrapeUrlValue(e.target.value)}
                placeholder="https://linkedin.com/jobs/view/…"
                required
                disabled={scraping}
                className="flex-1 px-3 py-2 border border-line rounded-xl text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500 min-w-0"
              />
              <button
                type="submit"
                disabled={scraping || !scrapeUrlValue}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-xl disabled:opacity-50 whitespace-nowrap"
              >
                {scraping ? 'Extracting…' : 'Extract'}
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Search + sort toolbar */}
      {(loading || jobs.length > 0) && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-fg-subtle" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by company or job title…"
              className="w-full pl-9 pr-4 py-2.5 border border-line rounded-xl text-sm bg-surface text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'date' | 'alpha')}
            className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="date">Newest saved</option>
            <option value="alpha">A–Z by title</option>
          </select>
        </div>
      )}

      {/* Job list */}
      {loading ? (
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => <JdSkeleton key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-surface rounded-2xl border border-line flex flex-col items-center justify-center py-16 px-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-surface">
            {search ? (
              <MagnifyingGlassIcon className="h-6 w-6 text-fg-subtle" />
            ) : (
              <BookmarkIcon className="h-6 w-6 text-fg-subtle" />
            )}
          </div>
          <h2 className="mt-4 text-sm font-semibold text-fg">
            {search ? 'No results found' : 'No jobs yet'}
          </h2>
          <p className="mt-1 text-sm text-fg-subtle">
            {search
              ? `No jobs match "${search}"`
              : 'Save jobs from Discover or add a job description to get started.'}
          </p>
          {!search && (
            <div className="mt-4 flex gap-3">
              <Link
                to="/discover"
                className="inline-block rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
              >
                Discover Jobs
              </Link>
              <button
                onClick={() => { reset(); setAddOpen(true) }}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-text hover:text-accent-text transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
                Add manually
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((job) => {
            const isExpanded = expandedId === job.id
            const desc = job.description ?? ''
            const hasLong = desc.length > 150
            return (
              <div key={job.id} onClick={() => handleCardClick(job)} className="bg-surface rounded-2xl border border-line p-5 hover:border-line-strong transition-colors cursor-pointer">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 bg-chip-accent rounded-xl flex items-center justify-center flex-shrink-0">
                    <BriefcaseIcon className="h-5 w-5 text-accent-text" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold text-fg">{job.job_title}</h3>
                    <p className="truncate text-sm text-fg-subtle">{job.company_name}</p>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-1">
                    {job.list_name && (
                      <span className="text-xs rounded-full bg-primary-900/20 px-2 py-0.5 text-accent-text hidden sm:inline-block">
                        {job.list_name}
                      </span>
                    )}
                    <span className="text-xs text-fg-subtle hidden sm:block">{formatDate(job.created_at)}</span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleStar(job.id, !job.starred) }}
                      className="rounded-lg p-1 text-fg-subtle transition-colors hover:text-chip-warn-fg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      aria-label={job.starred ? 'Unstar job' : 'Star job'}
                    >
                      {job.starred ? (
                        <StarSolid className="h-5 w-5 text-chip-warn-fg" />
                      ) : (
                        <StarIcon className="h-5 w-5" />
                      )}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(job) }}
                      className="h-8 w-8 flex items-center justify-center rounded-lg text-fg-subtle hover:text-chip-danger-fg hover:bg-chip-danger transition-colors"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-3">
                  <p className="text-sm text-fg-muted whitespace-pre-line">
                    {isExpanded ? desc : desc.slice(0, 150) + (hasLong ? '…' : '')}
                  </p>
                  {hasLong && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : job.id) }}
                      className="mt-1 inline-flex items-center gap-0.5 text-xs text-accent-text hover:text-accent-text"
                    >
                      {isExpanded ? <>Show less <ChevronUpIcon className="h-3 w-3" /></> : <>Read more <ChevronDownIcon className="h-3 w-3" /></>}
                    </button>
                  )}
                </div>

                {job.keywords && job.keywords.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {job.keywords.slice(0, 10).map((kw, i) => (
                      <span key={kw} className={`text-xs font-medium px-2 py-0.5 rounded-full ${KEYWORD_COLORS[i % KEYWORD_COLORS.length]}`}>
                        {kw}
                      </span>
                    ))}
                    {job.keywords.length > 10 && (
                      <span className="text-xs text-fg-subtle self-center">+{job.keywords.length - 10} more</span>
                    )}
                  </div>
                )}

                {(job.url || job.notes) && (
                  <div className="mt-2 flex flex-col gap-1">
                    {job.url && (
                      <a href={job.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-xs text-accent-text hover:underline truncate block">
                        {job.url}
                      </a>
                    )}
                    {job.notes && (
                      <p className="text-xs text-fg-subtle line-clamp-2 border-t border-line pt-1">
                        {job.notes}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Add Job Description modal */}
      <Dialog open={addOpen} onClose={() => !submitting && (setAddOpen(false), reset())} className="relative z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-surface rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-line flex-shrink-0">
              <DialogTitle className="text-base font-semibold text-fg">Add Job</DialogTitle>
              <button onClick={() => !submitting && (setAddOpen(false), reset())} className="h-8 w-8 flex items-center justify-center rounded-lg text-fg-subtle hover:text-fg-muted hover:bg-surface-strong">
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4 overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-fg-muted mb-1">Company name <span className="text-chip-danger-fg">*</span></label>
                  <input {...register('company_name')} placeholder="Acme Corp" className="w-full px-3 py-2 border border-line rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.company_name && <p className="mt-1 text-xs text-chip-danger-fg">{errors.company_name.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-fg-muted mb-1">Job title <span className="text-chip-danger-fg">*</span></label>
                  <input {...register('job_title')} placeholder="Senior Engineer" className="w-full px-3 py-2 border border-line rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.job_title && <p className="mt-1 text-xs text-chip-danger-fg">{errors.job_title.message}</p>}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-fg-muted mb-1">Job URL <span className="text-fg-subtle font-normal">(optional)</span></label>
                <input {...register('url')} type="url" placeholder="https://jobs.example.com/…" className="w-full px-3 py-2 border border-line rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                {errors.url && <p className="mt-1 text-xs text-chip-danger-fg">{errors.url.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-fg-muted mb-1">Job description <span className="text-chip-danger-fg">*</span></label>
                <textarea {...register('description')} rows={9} placeholder="Paste the full job description here. Keywords will be automatically extracted on save." className="w-full px-3 py-2 border border-line rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none" />
                {errors.description && <p className="mt-1 text-xs text-chip-danger-fg">{errors.description.message}</p>}
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => !submitting && (setAddOpen(false), reset())} disabled={submitting} className="px-4 py-2 text-sm font-medium text-fg-muted bg-surface hover:bg-surface-strong rounded-lg disabled:opacity-50">Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">
                  {submitting ? 'Saving…' : 'Save & Extract Keywords'}
                </button>
              </div>
            </form>
          </DialogPanel>
        </div>
      </Dialog>

      {/* Job detail modal (for discovered jobs) */}
      <JobDetail
        jobId={detailJobId}
        isSaved={true}
        onClose={() => setDetailJobId(null)}
        onSave={() => {}}
      />

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)} className="relative z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-surface rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-chip-danger rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-chip-danger-fg" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold text-fg">Delete Job</DialogTitle>
                <p className="mt-1 text-sm text-fg-subtle">
                  Delete <strong>"{deleteTarget?.job_title}" at {deleteTarget?.company_name}</strong>? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setDeleteTarget(null)} disabled={deleting} className="px-4 py-2 text-sm font-medium text-fg-muted bg-surface hover:bg-surface-strong rounded-lg disabled:opacity-50">Cancel</button>
              <button onClick={handleDelete} disabled={deleting} className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50">
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>
    </div>
  )
}
