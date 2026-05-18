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
  'bg-blue-100 text-blue-700',
  'bg-violet-100 text-violet-700',
  'bg-green-100 text-green-700',
  'bg-amber-100 text-amber-700',
  'bg-pink-100 text-pink-700',
  'bg-cyan-100 text-cyan-700',
  'bg-orange-100 text-orange-700',
]

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function JdSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-gray-100 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-4 bg-gray-100 rounded w-1/3" />
          <div className="h-3 bg-gray-100 rounded w-1/4" />
        </div>
      </div>
      <div className="flex gap-2">
        {[...Array(4)].map((_, i) => <div key={i} className="h-5 w-16 bg-gray-100 rounded-full" />)}
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Jobs</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Saved jobs from Discover and your job description library.
          </p>
        </div>
        {tab === 'descriptions' && (
          <button
            onClick={() => setAddOpen(true)}
            className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors self-start sm:self-auto flex-shrink-0"
          >
            <PlusIcon className="h-4 w-4" />
            Add Job Description
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-gray-100 p-1 dark:bg-gray-800 w-fit">
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
                ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {label}
            {count > 0 && (
              <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                tab === key ? 'bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-200' : 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
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
                <div key={i} className="h-36 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-800" />
              ))}
            </div>
          ) : saved.length === 0 ? (
            <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center dark:border-gray-700 dark:bg-gray-800">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gray-50 dark:bg-gray-700">
                <BookmarkIcon className="h-6 w-6 text-gray-400" />
              </div>
              <h2 className="mt-4 text-sm font-semibold text-gray-900 dark:text-white">No saved jobs yet</h2>
              <p className="mt-1 text-sm text-gray-400">
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
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
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
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
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
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by company or job title…"
                className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          )}

          {jdLoading ? (
            <div className="grid gap-4">
              {[...Array(3)].map((_, i) => <JdSkeleton key={i} />)}
            </div>
          ) : filteredJds.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 flex flex-col items-center justify-center py-16 px-6 text-center dark:border-gray-700 dark:bg-gray-800">
              <div className="h-12 w-12 bg-violet-100 rounded-xl flex items-center justify-center mb-3 dark:bg-violet-900/30">
                <BriefcaseIcon className="h-6 w-6 text-violet-400" />
              </div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                {search ? 'No results found' : 'No job descriptions yet'}
              </h3>
              <p className="mt-1 text-sm text-gray-400">
                {search ? `No jobs match "${search}"` : 'Add a job posting to extract keywords and tailor your CV.'}
              </p>
              {!search && (
                <button
                  onClick={() => setAddOpen(true)}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors"
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
                  <div key={job.id} className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-gray-300 transition-colors dark:border-gray-700 dark:bg-gray-800">
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 bg-violet-100 rounded-xl flex items-center justify-center flex-shrink-0 dark:bg-violet-900/30">
                        <BriefcaseIcon className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate text-sm font-semibold text-gray-900 dark:text-white">{job.job_title}</h3>
                        <p className="truncate text-sm text-gray-500 dark:text-gray-400">{job.company_name}</p>
                      </div>
                      <div className="flex flex-shrink-0 items-center gap-2">
                        <span className="text-xs text-gray-400 hidden sm:block">{formatDate(job.created_at)}</span>
                        <button
                          onClick={() => setDeleteTarget(job)}
                          className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3">
                      <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">
                        {isExpanded ? desc : desc.slice(0, 150) + (hasLong ? '…' : '')}
                      </p>
                      {hasLong && (
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : job.id)}
                          className="mt-1 inline-flex items-center gap-0.5 text-xs text-brand-600 hover:text-brand-700"
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
                          <span className="text-xs text-gray-400 self-center">+{job.keywords.length - 10} more</span>
                        )}
                      </div>
                    )}

                    {job.url && (
                      <a href={job.url} target="_blank" rel="noopener noreferrer" className="mt-2 text-xs text-brand-600 hover:underline truncate block">
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
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
              <DialogTitle className="text-base font-semibold text-gray-900">Add Job Description</DialogTitle>
              <button onClick={() => !submitting && (setAddOpen(false), reset())} className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4 overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Company name <span className="text-red-500">*</span></label>
                  <input {...register('company_name')} placeholder="Acme Corp" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.company_name && <p className="mt-1 text-xs text-red-600">{errors.company_name.message}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Job title <span className="text-red-500">*</span></label>
                  <input {...register('job_title')} placeholder="Senior Engineer" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  {errors.job_title && <p className="mt-1 text-xs text-red-600">{errors.job_title.message}</p>}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Job URL <span className="text-gray-400 font-normal">(optional)</span></label>
                <input {...register('url')} type="url" placeholder="https://jobs.example.com/…" className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                {errors.url && <p className="mt-1 text-xs text-red-600">{errors.url.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Job description <span className="text-red-500">*</span></label>
                <textarea {...register('description')} rows={9} placeholder="Paste the full job description here. Keywords will be automatically extracted on save." className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none" />
                {errors.description && <p className="mt-1 text-xs text-red-600">{errors.description.message}</p>}
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => !submitting && (setAddOpen(false), reset())} disabled={submitting} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50">Cancel</button>
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
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <DialogTitle className="text-base font-semibold text-gray-900">Delete Job Description</DialogTitle>
                <p className="mt-1 text-sm text-gray-500">
                  Delete <strong>"{deleteTarget?.job_title}" at {deleteTarget?.company_name}</strong>? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setDeleteTarget(null)} disabled={deleting} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50">Cancel</button>
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
