import { useCallback, useEffect, useRef, useState } from 'react'
import type { AxiosError } from 'axios'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  PencilSquareIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { cvApi, jobApi } from '../services/api'
import { coverLetterApi } from '../services/coverLetterApi'
import type { CV, JobDescription } from '../types'
import type {
  CoverLetterJob,
  CoverLetterPreview,
  CoverLetterTone,
  CoverLetterUsage,
} from '../types/coverLetter'

type Step = 'select' | 'processing' | 'edit' | 'done'

const POLL_INTERVAL_MS = 2500

const TONE_OPTIONS: { value: CoverLetterTone; label: string; description: string }[] = [
  { value: 'formal', label: 'Formal', description: 'Professional, structured, 300–350 words' },
  { value: 'friendly', label: 'Friendly', description: 'Warm but professional, 300–350 words' },
  { value: 'concise', label: 'Concise', description: 'Short and direct, 200–250 words' },
]

export default function CoverLetter() {
  const [step, setStep] = useState<Step>('select')
  const [cvs, setCvs] = useState<CV[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [usage, setUsage] = useState<CoverLetterUsage | null>(null)
  const [loading, setLoading] = useState(true)

  const [selectedCvId, setSelectedCvId] = useState('')
  const [selectedJobId, setSelectedJobId] = useState('')
  const [tone, setTone] = useState<CoverLetterTone>('formal')
  const [submitting, setSubmitting] = useState(false)

  const [jobId, setJobId] = useState<string | null>(null)
  const [preview, setPreview] = useState<CoverLetterPreview | null>(null)
  const [editedText, setEditedText] = useState('')
  const [letterTitle, setLetterTitle] = useState('')
  const [saving, setSaving] = useState(false)

  const [history, setHistory] = useState<CoverLetterJob[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  const pollRef = useRef<number | null>(null)

  const refreshHistory = useCallback(() => {
    coverLetterApi
      .list()
      .then(setHistory)
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    Promise.all([cvApi.list(), jobApi.list(), coverLetterApi.getUsage()])
      .then(([cvList, jobList, usageInfo]) => {
        setCvs(cvList)
        setJobs(jobList)
        setUsage(usageInfo)
        const defaultCv = cvList.find((cv) => cv.is_default)
        if (defaultCv) setSelectedCvId(defaultCv.id)
        else if (cvList.length === 1) setSelectedCvId(cvList[0].id)
        if (jobList.length === 1) setSelectedJobId(jobList[0].id)
      })
      .catch(() => toast.error('Failed to load cover letter data'))
      .finally(() => setLoading(false))

    coverLetterApi
      .list()
      .then(setHistory)
      .catch(() => undefined)
      .finally(() => setHistoryLoading(false))
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
      const job = await coverLetterApi.submit(selectedCvId, selectedJobId, tone)
      setJobId(job.id)
      setStep('processing')
      startPolling(job.id)
    } catch (err: unknown) {
      const detail = (err as AxiosError<{ detail: string }>)?.response?.data?.detail
      toast.error(detail || 'Failed to start cover letter generation')
    } finally {
      setSubmitting(false)
    }
  }

  function startPolling(id: string) {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      try {
        const status = await coverLetterApi.getStatus(id)
        if (status.status === 'complete') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          const nextPreview = await coverLetterApi.getPreview(id)
          setPreview(nextPreview)
          setEditedText(nextPreview.generated_text)
          const selectedJob = jobs.find((j) => j.id === selectedJobId)
          if (selectedJob) {
            setLetterTitle(`Cover letter for ${selectedJob.job_title} at ${selectedJob.company_name}`)
          }
          setStep('edit')
          coverLetterApi.getUsage().then(setUsage).catch(() => undefined)
        } else if (status.status === 'failed') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          toast.error(status.error_message || 'Cover letter generation failed')
          setStep('select')
        }
      } catch {
        // Polling tolerates transient network errors.
      }
    }, POLL_INTERVAL_MS)
  }

  async function handleSave() {
    if (!jobId) return
    setSaving(true)
    try {
      await coverLetterApi.save(jobId, editedText, letterTitle || undefined)
      setStep('done')
      toast.success('Cover letter saved')
      refreshHistory()
    } catch (err: unknown) {
      toast.error(
        (err as AxiosError<{ detail: string }>)?.response?.data?.detail || 'Failed to save cover letter',
      )
    } finally {
      setSaving(false)
    }
  }

  function handleCopy() {
    navigator.clipboard
      .writeText(editedText)
      .then(() => toast.success('Copied to clipboard'))
      .catch(() => toast.error('Failed to copy'))
  }

  function handleDownload() {
    const blob = new Blob([editedText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${letterTitle || 'cover-letter'}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function handleReset() {
    if (pollRef.current) window.clearInterval(pollRef.current)
    setStep('select')
    setJobId(null)
    setPreview(null)
    setEditedText('')
    setLetterTitle('')
  }

  async function handleDelete(id: string) {
    try {
      await coverLetterApi.remove(id)
      setHistory((prev) => prev.filter((j) => j.id !== id))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const atLimit = Boolean(usage && usage.daily_limit !== null && usage.used_today >= usage.daily_limit)
  const canSubmit = Boolean(selectedCvId && selectedJobId && !submitting && !atLimit)
  const wordCount = editedText.trim() ? editedText.trim().split(/\s+/).length : 0

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <PencilSquareIcon className="h-7 w-7 text-brand-500" />
          Cover Letter Generator
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate a tailored cover letter for any job description, then edit and save it.
        </p>
      </div>

      {usage && <UsageBanner usage={usage} />}

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.18 }}
        >
          {step === 'select' && (
            <SelectStep
              cvs={cvs}
              jobs={jobs}
              loading={loading}
              selectedCvId={selectedCvId}
              selectedJobId={selectedJobId}
              tone={tone}
              onCvChange={setSelectedCvId}
              onJobChange={setSelectedJobId}
              onToneChange={setTone}
              onSubmit={handleSubmit}
              canSubmit={canSubmit}
              submitting={submitting}
              atLimit={atLimit}
            />
          )}

          {step === 'processing' && <ProcessingStep />}

          {step === 'edit' && preview && (
            <EditStep
              editedText={editedText}
              letterTitle={letterTitle}
              wordCount={wordCount}
              saving={saving}
              onTextChange={setEditedText}
              onTitleChange={setLetterTitle}
              onSave={handleSave}
              onCopy={handleCopy}
              onDownload={handleDownload}
              onBack={handleReset}
            />
          )}

          {step === 'done' && (
            <DoneStep
              letterTitle={letterTitle}
              savedText={editedText}
              onReset={handleReset}
              onCopy={handleCopy}
              onDownload={handleDownload}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {(history.length > 0 || historyLoading) && (
        <HistorySection
          history={history}
          loading={historyLoading}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}

function UsageBanner({ usage }: { usage: CoverLetterUsage }) {
  const resetTime = new Date(usage.resets_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
  const label =
    usage.daily_limit === null
      ? `${usage.used_today} used today. Admin access has no daily limit.`
      : `${usage.used_today} of ${usage.daily_limit} cover letters used today.`

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
  tone: CoverLetterTone
  onCvChange: (id: string) => void
  onJobChange: (id: string) => void
  onToneChange: (tone: CoverLetterTone) => void
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
  tone,
  onCvChange,
  onJobChange,
  onToneChange,
  onSubmit,
  canSubmit,
  submitting,
  atLimit,
}: SelectStepProps) {
  return (
    <div className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6">
      <div>
        <h2 className="text-sm font-semibold text-gray-700">Select CV and job description</h2>
        <p className="mt-1 text-xs text-gray-400">
          The AI will read your CV and the job description to generate a personalised cover letter.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-1">
          <label className="block text-xs font-medium text-gray-600">Your CV</label>
          {loading ? (
            <div className="h-10 animate-pulse rounded-lg bg-gray-100" />
          ) : cvs.length === 0 ? (
            <p className="text-xs text-gray-400">
              No CVs found.{' '}
              <a href="/cvs" className="underline">
                Upload one
              </a>
            </p>
          ) : (
            <select
              className="input w-full"
              value={selectedCvId}
              onChange={(e) => onCvChange(e.target.value)}
            >
              <option value="">— select a CV —</option>
              {cvs.map((cv) => (
                <option key={cv.id} value={cv.id}>
                  {cv.title}
                  {cv.is_default ? ' (default)' : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="space-y-1">
          <label className="block text-xs font-medium text-gray-600">Target job</label>
          {loading ? (
            <div className="h-10 animate-pulse rounded-lg bg-gray-100" />
          ) : jobs.length === 0 ? (
            <p className="text-xs text-gray-400">
              No job descriptions found.{' '}
              <a href="/jobs" className="underline">
                Add one
              </a>
            </p>
          ) : (
            <select
              className="input w-full"
              value={selectedJobId}
              onChange={(e) => onJobChange(e.target.value)}
            >
              <option value="">— select a job —</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.job_title} @ {job.company_name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-xs font-medium text-gray-600">Tone</label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {TONE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onToneChange(option.value)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                tone === option.value
                  ? 'border-brand-400 bg-brand-50 ring-1 ring-brand-400'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <p className="text-sm font-semibold text-gray-800">{option.label}</p>
              <p className="mt-0.5 text-xs text-gray-500">{option.description}</p>
            </button>
          ))}
        </div>
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
            Generating…
          </>
        ) : (
          <>
            <SparklesIcon className="h-4 w-4" />
            Generate cover letter
          </>
        )}
      </button>

      {atLimit && (
        <p className="text-sm text-red-600">
          Daily limit reached. Try again after the reset time or upgrade to premium.
        </p>
      )}
    </div>
  )
}

function ProcessingStep() {
  const [activeStep, setActiveStep] = useState(0)

  const steps = [
    { label: 'Parsing CV', sublabel: 'Extracting your experience' },
    { label: 'Detecting language', sublabel: 'Matching the output language' },
    { label: 'Analysing job description', sublabel: 'Identifying key requirements' },
    { label: 'Writing cover letter', sublabel: 'AI generation is in progress' },
    { label: 'Finalising', sublabel: 'Preparing your draft' },
  ]

  useEffect(() => {
    const delays = [2000, 4000, 8000, 20000]
    const timers = delays.map((delay, index) =>
      window.setTimeout(() => setActiveStep(index + 1), delay),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-8">
      <h2 className="mb-6 text-base font-semibold text-gray-900">Generating your cover letter</h2>
      <ol className="flex flex-col gap-4 sm:flex-row sm:items-start">
        {steps.map((s, index) => {
          const done = index < activeStep
          const active = index === activeStep
          return (
            <li key={s.label} className="flex min-w-0 items-start gap-3 sm:flex-1">
              <div
                className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-colors ${
                  done ? 'bg-green-500' : active ? 'animate-pulse bg-brand-500' : 'bg-gray-200'
                }`}
              >
                {done && (
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <div>
                <p className={`text-sm font-medium ${active ? 'text-gray-900' : done ? 'text-gray-500' : 'text-gray-400'}`}>
                  {s.label}
                </p>
                {active && <p className="mt-0.5 text-xs text-gray-400">{s.sublabel}</p>}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

interface EditStepProps {
  editedText: string
  letterTitle: string
  wordCount: number
  saving: boolean
  onTextChange: (text: string) => void
  onTitleChange: (title: string) => void
  onSave: () => void
  onCopy: () => void
  onDownload: () => void
  onBack: () => void
}

function EditStep({
  editedText,
  letterTitle,
  wordCount,
  saving,
  onTextChange,
  onTitleChange,
  onSave,
  onCopy,
  onDownload,
  onBack,
}: EditStepProps) {
  return (
    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Edit your cover letter</h2>
          <p className="mt-0.5 text-xs text-gray-400">
            Review and refine before saving. Changes are only saved when you click Save.
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500">
          {wordCount} words
        </span>
      </div>

      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-600">Title (optional)</label>
        <input
          type="text"
          className="input w-full"
          placeholder="e.g. Cover letter for Spotify"
          value={letterTitle}
          onChange={(e) => onTitleChange(e.target.value)}
        />
      </div>

      <textarea
        className="input min-h-[400px] w-full resize-y font-mono text-sm leading-relaxed"
        value={editedText}
        onChange={(e) => onTextChange(e.target.value)}
        spellCheck
      />

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onSave}
          disabled={saving || !editedText.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? (
            <>
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <DocumentTextIcon className="h-4 w-4" />
              Save
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <ClipboardDocumentIcon className="h-4 w-4" />
          Copy
        </button>

        <button
          type="button"
          onClick={onDownload}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <DocumentTextIcon className="h-4 w-4" />
          Download .txt
        </button>

        <button
          type="button"
          onClick={onBack}
          className="ml-auto text-sm text-gray-400 hover:text-gray-600"
        >
          Start over
        </button>
      </div>
    </div>
  )
}

interface DoneStepProps {
  letterTitle: string
  savedText: string
  onReset: () => void
  onCopy: () => void
  onDownload: () => void
}

function DoneStep({ letterTitle, savedText, onReset, onCopy, onDownload }: DoneStepProps) {
  return (
    <div className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <CheckCircleIcon className="h-8 w-8 text-green-500" />
        <div>
          <h2 className="text-base font-semibold text-gray-900">Cover letter saved!</h2>
          {letterTitle && <p className="text-sm text-gray-500">{letterTitle}</p>}
        </div>
      </div>

      <pre className="max-h-[400px] overflow-y-auto whitespace-pre-wrap rounded-xl bg-gray-50 p-4 text-sm leading-relaxed text-gray-700">
        {savedText}
      </pre>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <ClipboardDocumentIcon className="h-4 w-4" />
          Copy
        </button>

        <button
          type="button"
          onClick={onDownload}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <DocumentTextIcon className="h-4 w-4" />
          Download .txt
        </button>

        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          <SparklesIcon className="h-4 w-4" />
          Write another
        </button>
      </div>
    </div>
  )
}

interface HistorySectionProps {
  history: CoverLetterJob[]
  loading: boolean
  onDelete: (id: string) => void
}

function HistorySection({ history, loading, onDelete }: HistorySectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-2xl border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-6 py-4 text-sm font-semibold text-gray-700"
      >
        <span>History ({history.length})</span>
        <span className="text-gray-400">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="divide-y divide-gray-100 border-t border-gray-100">
          {loading ? (
            <div className="px-6 py-4 text-sm text-gray-400">Loading…</div>
          ) : history.length === 0 ? (
            <div className="px-6 py-4 text-sm text-gray-400">No cover letters yet.</div>
          ) : (
            history.map((job) => (
              <div key={job.id} className="flex items-center justify-between gap-4 px-6 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">
                    {job.title || 'Untitled cover letter'}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    {job.tone} · {job.status} ·{' '}
                    {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onDelete(job.id)}
                  className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                  title="Delete"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
