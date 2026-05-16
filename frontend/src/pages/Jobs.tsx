import { useEffect, useState } from 'react'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
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
import { jobApi } from '../services/api'
import type { CreateJobDescriptionRequest } from '../services/api'
import type { JobDescription } from '../types'

const jobSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  job_title: z.string().min(1, 'Job title is required'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  url: z
    .string()
    .url('Enter a valid URL')
    .optional()
    .or(z.literal('')),
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
  return new Date(s).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-gray-100 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-4 bg-gray-100 rounded w-1/3" />
          <div className="h-3 bg-gray-100 rounded w-1/4" />
        </div>
        <div className="h-3 bg-gray-100 rounded w-20 hidden sm:block" />
        <div className="h-8 w-8 bg-gray-100 rounded-lg" />
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-4/5" />
      </div>
      <div className="flex gap-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-5 w-16 bg-gray-100 rounded-full" />
        ))}
      </div>
    </div>
  )
}

export default function Jobs() {
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<JobDescription | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<JobFormData>({ resolver: zodResolver(jobSchema) })

  useEffect(() => {
    jobApi
      .list()
      .then(setJobs)
      .catch(() => toast.error('Failed to load job descriptions'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = jobs.filter((j) => {
    const q = search.toLowerCase()
    return (
      (j.company_name ?? '').toLowerCase().includes(q) ||
      (j.job_title ?? '').toLowerCase().includes(q)
    )
  })

  function closeAddModal() {
    if (!submitting) {
      setAddOpen(false)
      reset()
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
      toast.success('Job description added & keywords extracted!')
      setAddOpen(false)
      reset()
    } catch {
      toast.error('Failed to save job description')
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
      toast.success('Job description deleted')
      setDeleteTarget(null)
    } catch {
      toast.error('Could not delete job description')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Descriptions</h1>
          <p className="mt-1 text-sm text-gray-500">
            Add job postings to extract keywords and tailor your CV.
          </p>
        </div>
        <button
          onClick={() => setAddOpen(true)}
          className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors self-start sm:self-auto flex-shrink-0"
        >
          <PlusIcon className="h-4 w-4" />
          Add Job Description
        </button>
      </div>

      {/* Search */}
      {(loading || jobs.length > 0) && (
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by company or job title…"
            className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      )}

      {/* Job cards */}
      {loading ? (
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 flex flex-col items-center justify-center py-16 px-6 text-center">
          <div className="h-12 w-12 bg-violet-100 rounded-xl flex items-center justify-center mb-3">
            <BriefcaseIcon className="h-6 w-6 text-violet-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-900">
            {search ? 'No results found' : 'No job descriptions yet'}
          </h3>
          <p className="mt-1 text-sm text-gray-400">
            {search
              ? `No jobs match "${search}"`
              : 'Add your first job description to match against your CV.'}
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
          {filtered.map((job) => {
            const isExpanded = expandedId === job.id
            const desc = job.description ?? ''
            const hasLongDescription = desc.length > 150

            return (
              <div
                key={job.id}
                className="bg-white rounded-2xl border border-gray-200 p-5 hover:border-gray-300 transition-colors"
              >
                {/* Top row */}
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 bg-violet-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <BriefcaseIcon className="h-5 w-5 text-violet-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold leading-snug text-gray-900">
                      {job.job_title}
                    </h3>
                    <p className="truncate text-sm text-gray-500">{job.company_name}</p>
                  </div>
                  <div className="flex flex-shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
                    <span className="text-xs text-gray-400 hidden sm:block">
                      {formatDate(job.created_at)}
                    </span>
                    <button
                      onClick={() => setDeleteTarget(job)}
                      className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      title="Delete"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Description */}
                <div className="mt-3">
                  <p className="text-sm text-gray-600 whitespace-pre-line">
                    {isExpanded
                      ? desc
                      : desc.slice(0, 150) + (hasLongDescription ? '…' : '')}
                  </p>
                  {hasLongDescription && (
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : job.id)}
                      className="mt-1 inline-flex items-center gap-0.5 text-xs text-brand-600 hover:text-brand-700 transition-colors"
                    >
                      {isExpanded ? (
                        <>Show less <ChevronUpIcon className="h-3 w-3" /></>
                      ) : (
                        <>Read more <ChevronDownIcon className="h-3 w-3" /></>
                      )}
                    </button>
                  )}
                </div>

                {/* Keywords */}
                {job.keywords && job.keywords.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {job.keywords.slice(0, 10).map((kw, i) => (
                      <span
                        key={kw}
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          KEYWORD_COLORS[i % KEYWORD_COLORS.length]
                        }`}
                      >
                        {kw}
                      </span>
                    ))}
                    {job.keywords.length > 10 && (
                      <span className="text-xs text-gray-400 self-center">
                        +{job.keywords.length - 10} more
                      </span>
                    )}
                  </div>
                )}

                {/* URL */}
                {job.url && (
                  <div className="mt-2">
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand-600 hover:underline truncate block"
                    >
                      {job.url}
                    </a>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Add Job modal */}
      <Dialog open={addOpen} onClose={closeAddModal} className="relative z-50">
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
              <DialogTitle className="text-base font-semibold text-gray-900">
                Add Job Description
              </DialogTitle>
              <button
                onClick={closeAddModal}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="p-6 space-y-4 overflow-y-auto"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Company name <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('company_name')}
                    placeholder="Acme Corp"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  {errors.company_name && (
                    <p className="mt-1 text-xs text-red-600">
                      {errors.company_name.message}
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Job title <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('job_title')}
                    placeholder="Senior Engineer"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  {errors.job_title && (
                    <p className="mt-1 text-xs text-red-600">
                      {errors.job_title.message}
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Job URL{' '}
                  <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  {...register('url')}
                  type="url"
                  placeholder="https://jobs.example.com/…"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                {errors.url && (
                  <p className="mt-1 text-xs text-red-600">{errors.url.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Job description <span className="text-red-500">*</span>
                </label>
                <textarea
                  {...register('description')}
                  rows={9}
                  placeholder="Paste the full job description here. Keywords will be automatically extracted on save."
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                />
                {errors.description && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.description.message}
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={closeAddModal}
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {submitting ? 'Saving…' : 'Save & Extract Keywords'}
                </button>
              </div>
            </form>
          </DialogPanel>
        </div>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleting && setDeleteTarget(null)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base font-semibold text-gray-900">
                  Delete Job Description
                </DialogTitle>
                <p className="mt-1 text-sm text-gray-500">
                  Delete{' '}
                  <strong>
                    "{deleteTarget?.job_title}" at {deleteTarget?.company_name}
                  </strong>
                  ? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>
    </div>
  )
}
