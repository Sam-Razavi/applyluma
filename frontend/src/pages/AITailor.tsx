import { useEffect, useRef, useState } from 'react'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { IntensitySelector } from '../components/tailor/IntensitySelector'
import { SectionDiff } from '../components/tailor/SectionDiff'
import { TailorProgress } from '../components/tailor/TailorProgress'
import { TailorSummary } from '../components/tailor/TailorSummary'
import { cvApi, jobApi } from '../services/api'
import { tailorApi } from '../services/tailorApi'
import type { CV, JobDescription } from '../types'
import type { TailorIntensity, TailorPreview, TailorUsage } from '../types/tailor'

type Step = 'select' | 'processing' | 'preview' | 'done'

const POLL_INTERVAL_MS = 2500

export default function AITailor() {
  const [step, setStep] = useState<Step>('select')
  const [cvs, setCvs] = useState<CV[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [usage, setUsage] = useState<TailorUsage | null>(null)
  const [loading, setLoading] = useState(true)

  const [selectedCvId, setSelectedCvId] = useState('')
  const [selectedJobId, setSelectedJobId] = useState('')
  const [intensity, setIntensity] = useState<TailorIntensity>('medium')

  const [jobId, setJobId] = useState<string | null>(null)
  const [preview, setPreview] = useState<TailorPreview | null>(null)
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set())
  const [savedCvId, setSavedCvId] = useState<string | null>(null)
  const [savedTitle, setSavedTitle] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    Promise.all([cvApi.list(), jobApi.list(), tailorApi.getUsage()])
      .then(([cvList, jobList, usageInfo]) => {
        setCvs(cvList)
        setJobs(jobList)
        setUsage(usageInfo)
        const defaultCv = cvList.find((cv) => cv.is_default)
        if (defaultCv) setSelectedCvId(defaultCv.id)
        else if (cvList.length === 1) setSelectedCvId(cvList[0].id)
        if (jobList.length === 1) setSelectedJobId(jobList[0].id)
      })
      .catch(() => toast.error('Failed to load tailoring data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [])

  async function handleSubmit() {
    if (!selectedCvId || !selectedJobId) return
    setSubmitting(true)
    try {
      const job = await tailorApi.submit(selectedCvId, selectedJobId, intensity)
      setJobId(job.id)
      setStep('processing')
      startPolling(job.id)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      toast.error(detail || 'Failed to start tailoring')
    } finally {
      setSubmitting(false)
    }
  }

  function startPolling(id: string) {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      try {
        const status = await tailorApi.getStatus(id)
        if (status.status === 'complete') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          const nextPreview = await tailorApi.getPreview(id)
          setPreview(nextPreview)
          setAcceptedIds(new Set(nextPreview.sections.map((section) => section.section_id)))
          setStep('preview')
        } else if (status.status === 'failed') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          toast.error(status.error_message || 'Tailoring failed')
          setStep('select')
        }
      } catch {
        // Polling tolerates transient network errors.
      }
    }, POLL_INTERVAL_MS)
  }

  function toggleSection(id: string) {
    setAcceptedIds((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSave(cvTitle?: string) {
    if (!jobId || !preview) return
    setSaving(true)
    try {
      const result = await tailorApi.save(
        jobId,
        acceptedIds.size === preview.sections.length ? null : [...acceptedIds],
        cvTitle,
      )
      setSavedCvId(result.cv_id)
      setSavedTitle(result.title)
      setStep('done')
      toast.success('Tailored CV saved')
      tailorApi.getUsage().then(setUsage).catch(() => undefined)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save tailored CV')
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    if (pollRef.current) window.clearInterval(pollRef.current)
    setStep('select')
    setJobId(null)
    setPreview(null)
    setAcceptedIds(new Set())
    setSavedCvId(null)
    setSavedTitle('')
  }

  const selectedCv = cvs.find((cv) => cv.id === selectedCvId)
  const selectedJob = jobs.find((job) => job.id === selectedJobId)
  const atLimit = Boolean(usage && usage.daily_limit !== null && usage.used_today >= usage.daily_limit)
  const canSubmit = Boolean(selectedCvId && selectedJobId && !submitting && !atLimit)

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <SparklesIcon className="h-7 w-7 text-brand-500" />
          AI CV Tailor
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Rewrite your CV for a specific job, review every section, and save a tailored PDF.
        </p>
      </div>

      {usage && <UsageBanner usage={usage} />}

      {step === 'select' && (
        <SelectStep
          cvs={cvs}
          jobs={jobs}
          loading={loading}
          selectedCvId={selectedCvId}
          selectedJobId={selectedJobId}
          selectedCv={selectedCv}
          selectedJob={selectedJob}
          intensity={intensity}
          onCvChange={setSelectedCvId}
          onJobChange={setSelectedJobId}
          onIntensityChange={setIntensity}
          onSubmit={handleSubmit}
          canSubmit={canSubmit}
          submitting={submitting}
          atLimit={atLimit}
        />
      )}

      {step === 'processing' && <TailorProgress />}

      {step === 'preview' && preview && (
        <PreviewStep
          preview={preview}
          acceptedIds={acceptedIds}
          onToggle={toggleSection}
          onSave={handleSave}
          onBack={handleReset}
          saving={saving}
        />
      )}

      {step === 'done' && savedCvId && jobId && (
        <DoneStep cvId={savedCvId} savedTitle={savedTitle} onReset={handleReset} />
      )}
    </div>
  )
}

function UsageBanner({ usage }: { usage: TailorUsage }) {
  const resetTime = new Date(usage.resets_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
  const label =
    usage.daily_limit === null
      ? `${usage.used_today} used today. Admin access has no daily limit.`
      : `${usage.used_today} of ${usage.daily_limit} tailoring runs used today.`

  return (
    <div className="rounded-xl border border-brand-100 bg-brand-50 px-4 py-3">
      <p className="text-sm font-medium text-brand-900">{label}</p>
      <p className="mt-0.5 text-xs text-brand-700">Resets at {resetTime} UTC.</p>
    </div>
  )
}

interface SelectStepProps {
  cvs: CV[]
  jobs: JobDescription[]
  loading: boolean
  selectedCvId: string
  selectedJobId: string
  selectedCv: CV | undefined
  selectedJob: JobDescription | undefined
  intensity: TailorIntensity
  onCvChange: (value: string) => void
  onJobChange: (value: string) => void
  onIntensityChange: (value: TailorIntensity) => void
  onSubmit: () => void
  canSubmit: boolean
  submitting: boolean
  atLimit: boolean
}

function SelectStep({
  cvs,
  jobs,
  loading,
  selectedCvId,
  selectedJobId,
  selectedCv,
  selectedJob,
  intensity,
  onCvChange,
  onJobChange,
  onIntensityChange,
  onSubmit,
  canSubmit,
  submitting,
  atLimit,
}: SelectStepProps) {
  return (
    <div className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6">
      <div>
        <h2 className="text-sm font-semibold text-gray-700">Select source CV and target job</h2>
        <p className="mt-1 text-xs text-gray-400">
          The original CV remains unchanged. A tailored copy is created only after you save.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Selector
          label="Your CV"
          value={selectedCvId}
          onChange={onCvChange}
          loading={loading}
          emptyMessage="No CVs found"
          emptyHref="/cvs"
          emptyLinkLabel="Upload one"
          options={cvs.map((cv) => ({
            value: cv.id,
            label: `${cv.title}${cv.is_default ? ' (default)' : ''}`,
          }))}
        />
        <Selector
          label="Target job"
          value={selectedJobId}
          onChange={onJobChange}
          loading={loading}
          emptyMessage="No job descriptions found"
          emptyHref="/jobs"
          emptyLinkLabel="Add one"
          options={jobs.map((job) => ({
            value: job.id,
            label: `${job.job_title} @ ${job.company_name}`,
          }))}
        />
      </div>

      {(selectedCv || selectedJob) && (
        <div className="flex flex-wrap gap-2">
          {selectedCv && <Pill>{selectedCv.title}</Pill>}
          {selectedJob && <Pill>{`${selectedJob.job_title} @ ${selectedJob.company_name}`}</Pill>}
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Tailoring intensity</h3>
        <IntensitySelector value={intensity} onChange={onIntensityChange} />
      </div>

      <button
        type="button"
        onClick={onSubmit}
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? (
          <>
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            Starting tailoring
          </>
        ) : (
          <>
            <SparklesIcon className="h-4 w-4" />
            Tailor CV
          </>
        )}
      </button>

      {atLimit && (
        <p className="text-sm text-red-600">
          Daily tailoring limit reached. Try again after the reset time.
        </p>
      )}
    </div>
  )
}

interface SelectorProps {
  label: string
  value: string
  onChange: (value: string) => void
  loading: boolean
  emptyMessage: string
  emptyHref: string
  emptyLinkLabel: string
  options: { value: string; label: string }[]
}

function Selector({
  label,
  value,
  onChange,
  loading,
  emptyMessage,
  emptyHref,
  emptyLinkLabel,
  options,
}: SelectorProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium uppercase tracking-wide text-gray-600">{label}</label>
      {loading ? (
        <div className="h-10 animate-pulse rounded-lg bg-gray-100" />
      ) : options.length === 0 ? (
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-3 py-2.5 text-sm text-gray-400">
          {emptyMessage}
          <Link to={emptyHref} className="text-brand-600 hover:underline">
            {emptyLinkLabel}
          </Link>
        </div>
      ) : (
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Choose...</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}

function Pill({ children }: { children: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
      <CheckCircleIcon className="h-3.5 w-3.5" />
      {children}
    </span>
  )
}

interface PreviewStepProps {
  preview: TailorPreview
  acceptedIds: Set<string>
  onToggle: (sectionId: string) => void
  onSave: (cvTitle?: string) => void
  onBack: () => void
  saving: boolean
}

function PreviewStep({
  preview,
  acceptedIds,
  onToggle,
  onSave,
  onBack,
  saving,
}: PreviewStepProps) {
  const [title, setTitle] = useState('')

  return (
    <div className="space-y-5">
      <TailorSummary meta={preview.meta} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Review section changes</h2>
          <p className="mt-1 text-sm text-gray-500">
            Accepted sections use tailored text. Rejected sections keep the original text.
          </p>
        </div>
        <div className="text-sm text-gray-500">
          {acceptedIds.size} of {preview.sections.length} accepted
        </div>
      </div>

      <div className="space-y-4">
        {preview.sections.map((section) => (
          <SectionDiff
            key={section.section_id}
            section={section}
            accepted={acceptedIds.has(section.section_id)}
            onToggle={() => onToggle(section.section_id)}
          />
        ))}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <label className="text-xs font-medium uppercase tracking-wide text-gray-600">
          Saved CV title
        </label>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Tailored CV"
          className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onBack}
            disabled={saving}
            className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
          >
            Start over
          </button>
          <button
            type="button"
            onClick={() => onSave(title || undefined)}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
          >
            {saving && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            Save tailored PDF
          </button>
        </div>
      </div>
    </div>
  )
}

function DoneStep({
  cvId,
  savedTitle,
  onReset,
}: {
  cvId: string
  savedTitle: string
  onReset: () => void
}) {
  const [downloading, setDownloading] = useState(false)

  async function handleDownload() {
    setDownloading(true)
    try {
      const filename = savedTitle ? `${savedTitle}.pdf` : 'tailored-cv.pdf'
      await cvApi.download(cvId, filename)
    } catch {
      toast.error('Could not download the tailored CV')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-green-50">
        <DocumentTextIcon className="h-6 w-6 text-green-600" />
      </div>
      <h2 className="mt-4 text-lg font-semibold text-gray-900">Tailored CV saved</h2>
      <p className="mt-1 text-sm text-gray-500">
        Your tailored PDF was saved as a new CV. The original remains unchanged.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {downloading ? (
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowDownTrayIcon className="h-4 w-4" />
          )}
          Download PDF
        </button>
        <Link
          to="/cvs"
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200"
        >
          View in My CVs
        </Link>
        <button
          type="button"
          onClick={onReset}
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200"
        >
          Tailor another
        </button>
      </div>
    </div>
  )
}
