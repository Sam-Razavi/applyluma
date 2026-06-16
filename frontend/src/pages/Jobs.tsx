import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
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
import toast from 'react-hot-toast'
import SavedJobCard from '../components/discover/SavedJobCard'
import JobDetail from '../components/discover/JobDetail'
import { jobApi } from '../services/api'
import type { CreateJobDescriptionRequest } from '../services/api'
import { fetchSavedJobs, fetchJobDetail, updateSavedJob, deleteSavedJob } from '../services/jobDiscoveryApi'
import type { JobDescription } from '../types'
import type { SavedJob } from '../types/jobDiscovery'

const jobSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  job_title: z.string().min(1, 'Job title is required'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  url: z.string().url('Enter a valid URL').optional().or(z.literal('')),
})
type JobFormData = z.infer<typeof jobSchema>

const KEYWORD_COLORS = [
  'bg-[rgba(8,145,178,0.15)] text-cyan-300',
  'bg-[rgba(8,145,178,0.15)] text-cyan-300',
  'bg-[rgba(52,195,143,0.14)] text-emerald-300',
  'bg-[rgba(245,158,11,0.14)] text-amber-300',
  'bg-[rgba(8,145,178,0.15)] text-pink-700',
  'bg-cyan-100 text-cyan-700',
  'bg-[rgba(245,158,11,0.14)] text-amber-300',
]

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function JdSkeleton() {
  return (
    <div className="bg-white/[0.04] rounded-2xl border border-white/10 p-5 space-y-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-white/[0.04] rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-4 bg-white/[0.04] rounded w-1/3" />
          <div className="h-3 bg-white/[0.04] rounded w-1/4" />
        </div>
      </div>
      <div className="flex gap-2">
        {[...Array(4)].map((_, i) => <div key={i} className="h-5 w-16 bg-white/[0.04] rounded-full" />)}
      </div>
    </div>
  )
}

type Tab = 'saved' | 'descriptions'

export default function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as Tab) ?? 'saved'
  const [tab, setTab] = useState<Tab>(initialTab)

  function switchTab(t: Tab) {
    setTab(t)
    setSearchParams(t === 'saved' ? {} : { tab: t }, { replace: true })
  }

  // ── Saved jobs ───────────────────────────────────────────────────────────
  const [saved, setSaved] = useState<SavedJob[]>([])
  const [savedLoading, setSavedLoading] = useState(true)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [activeCollection, setActiveCollection] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Jobs | ApplyLuma'
    fetchSavedJobs()
      .then(setSaved)
      .catch(() => toast.error('Failed to load saved jobs'))
      .finally(() => setSavedLoading(false))
  }, [])

  async function handleStar(savedId: string, starred: boolean) {
    setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred } : s)))
    try {
      const updated = await updateSavedJob(savedId, { starred })
      setSaved((prev) => prev.map((s) => (s.id === savedId ? updated : s)))
    } catch {
      setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred: !starred } : s)))
      toast.error('Failed to update')
    }
  }

  async function handleDeleteSaved(savedId: string) {
    const removed = saved.find((s) => s.id === savedId)
    setSaved((prev) => prev.filter((s) => s.id !== savedId))
    toast.success('Removed from saved jobs')
    try {
      await deleteSavedJob(savedId)
    } catch {
      if (removed) setSaved((prev) => [...prev, removed])
      toast.error('Failed to remove')
    }
  }

  const collections = [...new Set(saved.map((s) => s.list_name ?? 'Saved'))]
  const displayedSaved =
    activeCollection === null
      ? saved
      : saved.filter((s) => (s.list_name ?? 'Saved') === activeCollection)

  // ── Job descriptions ─────────────────────────────────────────────────────
  const [jds, setJds] = useState<JobDescription[]>([])
  const [jdLoading, setJdLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<JobDescription | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [addingFromSavedId, setAddingFromSavedId] = useState<string | null>(null)
  const [urlBarOpen, setUrlBarOpen] = useState(false)
  const [scrapeUrlValue, setScrapeUrlValue] = useState('')
  const [scraping, setScraping] = useState(false)

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<JobFormData>({
    resolver: zodResolver(jobSchema),
  })

  useEffect(() => {
    jobApi
      .list()
      .then(setJds)
      .catch(() => toast.error('Failed to load job descriptions'))
      .finally(() => setJdLoading(false))
  }, [])

  const filteredJds = jds.filter((j) => {
    const q = search.toLowerCase()
    return (
      (j.company_name ?? '').toLowerCase().includes(q) ||
      (j.job_title ?? '').toLowerCase().includes(q)
    )
  })

  async function handleAddToDescriptions(saved: SavedJob) {
    setAddingFromSavedId(saved.id)
    try {
      const detail = await fetchJobDetail(saved.raw_job_posting_id)
      reset()
      setValue('company_name', detail.company ?? '')
      setValue('job_title', detail.title ?? '')
      setValue('description', detail.description ?? '')
      if (detail.url) setValue('url', detail.url)
      setAddOpen(true)
    } catch {
      toast.error('Failed to load job details')
    } finally {
      setAddingFromSavedId(null)
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
    } catch {
      toast.error('Could not extract job details from that URL')
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
      setJds((prev) => [jd, ...prev])
      toast.success('Job description added & keywords extracted!')
      setAddOpen(false)
      reset()
    } catch {
      toast.error('Failed to save job description')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDeleteJd() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await jobApi.remove(deleteTarget.id)
      setJds((prev) => prev.filter((j) => j.id !== deleteTarget.id))
      toast.success('Job description deleted')
      setDeleteTarget(null)
    } catch {
      toast.error('Could not delete job description')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white/90 ">Jobs</h1>
          <p className="mt-1 text-sm text-white/30 ">
            Saved jobs from Discover and your job description library.
          </p>
        </div>
        {tab === 'descriptions' && (
          <div className="flex flex-col gap-2 self-start sm:self-auto">
            <div className="flex gap-2">
              <button
                onClick={() => { setUrlBarOpen((o) => !o); setScrapeUrlValue('') }}
                className="inline-flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.04] text-white/55 text-sm font-semibold px-4 py-2.5 rounded-xl border border-white/10 transition-colors "
              >
                <LinkIcon className="h-4 w-4" />
                Import from URL
              </button>
              <button
                onClick={() => setAddOpen(true)}
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
                  className="flex-1 px-3 py-2 border border-white/10 rounded-xl text-sm bg-white/[0.04] focus:outline-none focus:ring-2 focus:ring-brand-500 min-w-0"
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
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-white/[0.04] p-1 w-fit">
        {([
          { key: 'saved', label: 'Saved Jobs', count: saved.length },
          { key: 'descriptions', label: 'Job Descriptions', count: jds.length },
        ] as { key: Tab; label: string; count: number }[]).map(({ key, label, count }) => (
          <button
            key={key}
            type="button"
            onClick={() => switchTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab === key
                ? 'bg-white/[0.04] text-white/90 shadow-sm '
                : 'text-white/30 hover:text-white/55 '
            }`}
          >
            {label}
            {count > 0 && (
              <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                tab === key ? 'bg-white/[0.04] text-white/55 ' : 'bg-white/[0.06] text-white/30 '
              }`}>
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Saved Jobs tab ───────────────────────────────────────────────── */}
      {tab === 'saved' && (
        <>
          {savedLoading ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-36 animate-pulse rounded-2xl bg-white/[0.04] " />
              ))}
            </div>
          ) : saved.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-16 text-center ">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.03] ">
                <BookmarkIcon className="h-6 w-6 text-white/30" />
              </div>
              <h2 className="mt-4 text-sm font-semibold text-white/90 ">No saved jobs yet</h2>
              <p className="mt-1 text-sm text-white/30">
                Browse Discover and bookmark jobs you're interested in.
              </p>
              <Link
                to="/discover"
                className="mt-4 inline-block rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
              >
                Discover Jobs
              </Link>
            </div>
          ) : (
            <>
              {collections.length > 1 && (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  <button
                    type="button"
                    onClick={() => setActiveCollection(null)}
                    className={`rounded-full px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors ${
                      activeCollection === null
                        ? 'bg-brand-600 text-white'
                        : 'bg-white/[0.04] text-white/55 hover:bg-white/[0.08] '
                    }`}
                  >
                    All ({saved.length})
                  </button>
                  {collections.map((col) => (
                    <button
                      key={col}
                      type="button"
                      onClick={() => setActiveCollection(col)}
                      className={`rounded-full px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors ${
                        activeCollection === col
                          ? 'bg-brand-600 text-white'
                          : 'bg-white/[0.04] text-white/55 hover:bg-white/[0.08] '
                      }`}
                    >
                      {col} ({saved.filter((s) => (s.list_name ?? 'Saved') === col).length})
                    </button>
                  ))}
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                {displayedSaved.map((s) => (
                  <SavedJobCard
                    key={s.id}
                    saved={s}
                    onClick={setSelectedJobId}
                    onStar={handleStar}
                    onDelete={handleDeleteSaved}
                    onAddToDescriptions={handleAddToDescriptions}
                    addingToDescriptions={addingFromSavedId === s.id}
                  />
                ))}
              </div>
            </>
          )}

          <JobDetail
            jobId={selectedJobId}
            isSaved={true}
            onClose={() => setSelectedJobId(null)}
            onSave={() => {}}
          />
        </>
      )}

      {/* ── Job Descriptions tab ─────────────────────────────────────────── */}
      {tab === 'descriptions' && (
        <>
          {(jdLoading || jds.length > 0) && (
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by company or job title…"
                className="w-full pl-9 pr-4 py-2.5 border border-white/10 rounded-xl text-sm bg-white/[0.04] focus:outline-none focus:ring-2 focus:ring-brand-500 "
              />
            </div>
          )}

          {jdLoading ? (
            <div className="grid gap-4">
              {[...Array(3)].map((_, i) => <JdSkeleton key={i} />)}
            </div>
          ) : filteredJds.length === 0 ? (
            <div className="bg-white/[0.04] rounded-2xl border border-white/10 flex flex-col items-center justify-center py-16 px-6 text-center ">
              <div className="h-12 w-12 bg-[rgba(8,145,178,0.15)] rounded-xl flex items-center justify-center mb-3 ">
                <BriefcaseIcon className="h-6 w-6 text-violet-400" />
              </div>
              <h3 className="text-sm font-medium text-white/90 ">
                {search ? 'No results found' : 'No job descriptions yet'}
              </h3>
              <p className="mt-1 text-sm text-white/30">
                {search ? `No jobs match "${search}"` : 'Add a job posting to extract keywords and tailor your CV.'}
              </p>
              {!search && (
                <button
                  onClick={() => setAddOpen(true)}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary-400 hover:text-primary-300 transition-colors"
                >
                  <PlusIcon className="h-4 w-4" />
                  Add a job description
                </button>
              )}
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredJds.map((job) => {
                const isExpanded = expandedId === job.id
                const desc = job.description ?? ''
                const hasLong = desc.length > 150
                return (
                  <div key={job.id} className="bg-white/[0.04] rounded-2xl border border-white/10 p-5 hover:border-white/20 transition-colors ">
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 bg-[rgba(8,145,178,0.15)] rounded-xl flex items-center justify-center flex-shrink-0 ">
                        <BriefcaseIcon className="h-5 w-5 text-cyan-300 " />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate text-sm font-semibold text-white/90 ">{job.job_title}</h3>
                        <p className="truncate text-sm text-white/30 ">{job.company_name}</p>
                      </div>
                      <div className="flex flex-shrink-0 items-center gap-2">
                        <span className="text-xs text-white/30 hidden sm:block">{formatDate(job.created_at)}</span>
                        <button
                          onClick={() => setDeleteTarget(job)}
                          className="h-8 w-8 flex items-center justify-center rounded-lg text-white/30 text-red-300 hover:bg-[rgba(229,72,77,0.12)] transition-colors"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3">
                      <p className="text-sm text-white/55 whitespace-pre-line">
                        {isExpanded ? desc : desc.slice(0, 150) + (hasLong ? '…' : '')}
                      </p>
                      {hasLong && (
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : job.id)}
                          className="mt-1 inline-flex items-center gap-0.5 text-xs text-primary-400 hover:text-primary-300"
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
                          <span className="text-xs text-white/30 self-center">+{job.keywords.length - 10} more</span>
                        )}
                      </div>
                    )}

                    {job.url && (
                      <a href={job.url} target="_blank" rel="noopener noreferrer" className="mt-2 text-xs text-primary-400 hover:underline truncate block">
                        {job.url}
                      </a>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* Add Job Description modal */}
      <Dialog open={addOpen} onClose={() => !submitting && (setAddOpen(false), reset())} className="relative z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white/[0.04] rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 flex-shrink-0">
              <DialogTitle className="text-base font-semibold text-white/90">Add Job Description</DialogTitle>
              <button onClick={() => !submitting && (setAddOpen(false), reset())} className="h-8 w-8 flex items-center justify-center rounded-lg text-white/30 hover:text-white/55 hover:bg-white/[0.06]">
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4 overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-white/55 mb-1">Company name <span className="text-red-500">*</span></label>
                  <input {...register('company_name')} placeholder="Acme Corp" className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.company_name && <p className="mt-1 text-xs text-red-300">{errors.company_name.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/55 mb-1">Job title <span className="text-red-500">*</span></label>
                  <input {...register('job_title')} placeholder="Senior Engineer" className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.job_title && <p className="mt-1 text-xs text-red-300">{errors.job_title.message}</p>}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-white/55 mb-1">Job URL <span className="text-white/30 font-normal">(optional)</span></label>
                <input {...register('url')} type="url" placeholder="https://jobs.example.com/…" className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                {errors.url && <p className="mt-1 text-xs text-red-300">{errors.url.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-white/55 mb-1">Job description <span className="text-red-500">*</span></label>
                <textarea {...register('description')} rows={9} placeholder="Paste the full job description here. Keywords will be automatically extracted on save." className="w-full px-3 py-2 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none" />
                {errors.description && <p className="mt-1 text-xs text-red-300">{errors.description.message}</p>}
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => !submitting && (setAddOpen(false), reset())} disabled={submitting} className="px-4 py-2 text-sm font-medium text-white/55 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg disabled:opacity-50">Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">
                  {submitting ? 'Saving…' : 'Save & Extract Keywords'}
                </button>
              </div>
            </form>
          </DialogPanel>
        </div>
      </Dialog>

      {/* Delete JD confirmation */}
      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)} className="relative z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white/[0.04] rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-[rgba(229,72,77,0.12)] rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-red-300" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold text-white/90">Delete Job Description</DialogTitle>
                <p className="mt-1 text-sm text-white/30">
                  Delete <strong>"{deleteTarget?.job_title}" at {deleteTarget?.company_name}</strong>? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setDeleteTarget(null)} disabled={deleting} className="px-4 py-2 text-sm font-medium text-white/55 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg disabled:opacity-50">Cancel</button>
              <button onClick={handleDeleteJd} disabled={deleting} className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50">
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>
    </div>
  )
}
