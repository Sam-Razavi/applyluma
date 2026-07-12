import { useCallback, useEffect, useRef, useState } from 'react'
import type { AxiosError } from 'axios'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  BriefcaseIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  EyeIcon,
  PencilSquareIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { AnimatePresence, motion } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { IntensitySelector } from '../components/tailor/IntensitySelector'
import { SectionDiff } from '../components/tailor/SectionDiff'
import { TailorSummary } from '../components/tailor/TailorSummary'
import { TemplatePicker } from '../components/tailor/TemplatePicker'
import { TemplatePreviewModal } from '../components/tailor/TemplatePreviewModal'
import { cvApi, jobApi } from '../services/api'
import { coverLetterApi } from '../services/coverLetterApi'
import { createApplication } from '../services/applicationsApi'
import { fetchJobDetail } from '../services/jobDiscoveryApi'
import { tailorApi } from '../services/tailorApi'
import { useAuthStore } from '../stores'
import type { CV, JobDescription } from '../types'
import type { DiscoveredJobDetail } from '../types/jobDiscovery'
import type { CvTemplateId, TailorIntensity, TailorPreview, TailorUsage } from '../types/tailor'
import type { CoverLetterJob, CoverLetterTone, CoverLetterUsage } from '../types/coverLetter'

type Step = 'select' | 'processing' | 'review' | 'done'

const POLL_INTERVAL_MS = 2500

const TEMPLATE_IDS: CvTemplateId[] = ['nordic', 'classic', 'modern', 'executive', 'atlas', 'compact']

/** Narrow the wire value (users.preferred_template) to a known template id. */
function resolveTemplate(value?: string | null): CvTemplateId {
  return TEMPLATE_IDS.includes(value as CvTemplateId) ? (value as CvTemplateId) : 'nordic'
}

const TONE_OPTIONS: { value: CoverLetterTone; label: string; description: string }[] = [
  { value: 'formal', label: 'Formal', description: 'Professional, structured, 300–350 words' },
  { value: 'friendly', label: 'Friendly', description: 'Warm but professional, 300–350 words' },
  { value: 'concise', label: 'Concise', description: 'Short and direct, 200–250 words' },
]

export default function AITailor() {
  const location = useLocation()
  const locationState = location.state as {
    rawJobPostingId?: string
    jobTitle?: string
    company?: string
  } | null
  const rawJobPostingId = locationState?.rawJobPostingId

  const [step, setStep] = useState<Step>('select')
  const [cvs, setCvs] = useState<CV[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [rawJob, setRawJob] = useState<DiscoveredJobDetail | null>(null)
  const [tailorUsage, setTailorUsage] = useState<TailorUsage | null>(null)
  const [coverUsage, setCoverUsage] = useState<CoverLetterUsage | null>(null)
  const [loading, setLoading] = useState(true)

  const [selectedCvId, setSelectedCvId] = useState('')
  const [selectedJobId, setSelectedJobId] = useState('')
  const [wantCv, setWantCv] = useState(true)
  const [wantCover, setWantCover] = useState(true)
  const [intensity, setIntensity] = useState<TailorIntensity>('medium')
  const [tone, setTone] = useState<CoverLetterTone>('formal')
  const [submitting, setSubmitting] = useState(false)

  // CV tailoring result state.
  const [tailorJobId, setTailorJobId] = useState<string | null>(null)
  const [preview, setPreview] = useState<TailorPreview | null>(null)
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set())
  const [editedContent, setEditedContent] = useState<Map<string, string>>(new Map())
  const [sectionOrder, setSectionOrder] = useState<string[]>([])
  const [cvTitle, setCvTitle] = useState('')
  const preferredTemplate = resolveTemplate(useAuthStore((s) => s.user?.preferred_template))
  const [templateId, setTemplateId] = useState<CvTemplateId>(preferredTemplate)
  const [savedCvId, setSavedCvId] = useState<string | null>(null)
  const [savedCvTitle, setSavedCvTitle] = useState('')

  // Cover letter result state.
  const [coverJobId, setCoverJobId] = useState<string | null>(null)
  const [coverText, setCoverText] = useState('')
  const [coverTitle, setCoverTitle] = useState('')
  const [coverSaved, setCoverSaved] = useState(false)

  const [saving, setSaving] = useState(false)

  // Apply-loop state surfaced on the Done step.
  const [applicationStatus, setApplicationStatus] = useState<string | null>(null)
  const [addingApplication, setAddingApplication] = useState(false)

  const [history, setHistory] = useState<CoverLetterJob[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  const pollRef = useRef<number | null>(null)
  const cvReadyRef = useRef(false)
  const coverReadyRef = useRef(false)

  const refreshHistory = useCallback(() => {
    coverLetterApi
      .list()
      .then(setHistory)
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    const rawJobPromise = rawJobPostingId ? fetchJobDetail(rawJobPostingId) : Promise.resolve(null)
    Promise.all([
      cvApi.list(),
      jobApi.list(),
      tailorApi.getUsage(),
      coverLetterApi.getUsage(),
      rawJobPromise,
    ])
      .then(([cvList, jobList, tUsage, cUsage, discoveredJob]) => {
        setCvs(cvList)
        setJobs(jobList)
        setRawJob(discoveredJob)
        setApplicationStatus(discoveredJob?.application_status ?? null)
        setTailorUsage(tUsage)
        setCoverUsage(cUsage)
        const defaultCv = cvList.find((cv) => cv.is_default)
        if (defaultCv) setSelectedCvId(defaultCv.id)
        else if (cvList.length === 1) setSelectedCvId(cvList[0].id)
        if (!rawJobPostingId && jobList.length === 1) setSelectedJobId(jobList[0].id)
      })
      .catch(() => toast.error('Failed to load tailoring data'))
      .finally(() => setLoading(false))

    coverLetterApi
      .list()
      .then(setHistory)
      .catch(() => undefined)
      .finally(() => setHistoryLoading(false))
  }, [rawJobPostingId])

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [])

  function deriveJobLabel(): string {
    if (rawJobPostingId) {
      if (rawJob) return `${rawJob.title} at ${rawJob.company}`
      if (locationState?.jobTitle) {
        return `${locationState.jobTitle}${locationState.company ? ` at ${locationState.company}` : ''}`
      }
      return 'this role'
    }
    const job = jobs.find((j) => j.id === selectedJobId)
    return job ? `${job.job_title} at ${job.company_name}` : 'this role'
  }

  function failPolling(message: string) {
    if (pollRef.current) window.clearInterval(pollRef.current)
    toast.error(message)
    setStep('select')
  }

  function startPolling(enabledCv: boolean, enabledCover: boolean, cvId: string | null, coverId: string | null) {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      try {
        if (enabledCv && cvId && !cvReadyRef.current) {
          const status = await tailorApi.getStatus(cvId)
          if (status.status === 'complete') {
            const nextPreview = await tailorApi.getPreview(cvId)
            setPreview(nextPreview)
            setAcceptedIds(new Set(nextPreview.sections.map((s) => s.section_id)))
            setSectionOrder(nextPreview.sections.map((s) => s.section_id))
            setEditedContent(new Map())
            cvReadyRef.current = true
          } else if (status.status === 'failed') {
            failPolling(status.error_message || 'Tailoring failed')
            return
          }
        }

        if (enabledCover && coverId && !coverReadyRef.current) {
          const status = await coverLetterApi.getStatus(coverId)
          if (status.status === 'complete') {
            const nextPreview = await coverLetterApi.getPreview(coverId)
            setCoverText(nextPreview.generated_text)
            coverReadyRef.current = true
          } else if (status.status === 'failed') {
            failPolling(status.error_message || 'Cover letter generation failed')
            return
          }
        }

        const cvOk = !enabledCv || cvReadyRef.current
        const coverOk = !enabledCover || coverReadyRef.current
        if (cvOk && coverOk) {
          if (pollRef.current) window.clearInterval(pollRef.current)
          tailorApi.getUsage().then(setTailorUsage).catch(() => undefined)
          coverLetterApi.getUsage().then(setCoverUsage).catch(() => undefined)
          setStep('review')
        }
      } catch {
        // Polling tolerates transient network errors.
      }
    }, POLL_INTERVAL_MS)
  }

  async function handleSubmit() {
    if (!selectedCvId || (!selectedJobId && !rawJobPostingId)) return
    if (!wantCv && !wantCover) return
    setSubmitting(true)
    cvReadyRef.current = false
    coverReadyRef.current = false
    try {
      const [tailorJob, coverJob] = await Promise.all([
        wantCv
          ? tailorApi.submit(
              rawJobPostingId
                ? { cv_id: selectedCvId, raw_job_posting_id: rawJobPostingId, intensity }
                : { cv_id: selectedCvId, job_description_id: selectedJobId, intensity },
            )
          : Promise.resolve(null),
        wantCover
          ? coverLetterApi.submit(
              selectedCvId,
              rawJobPostingId ? null : selectedJobId,
              tone,
              rawJobPostingId ?? undefined,
            )
          : Promise.resolve(null),
      ])

      const jobLabel = deriveJobLabel()
      if (wantCover && !coverTitle) setCoverTitle(`Cover letter for ${jobLabel}`)

      import('posthog-js').then(({ default: posthog }) =>
        posthog.capture('ai_tailor_started', { intensity, want_cv: wantCv, want_cover: wantCover }),
      )

      setTailorJobId(tailorJob?.id ?? null)
      setCoverJobId(coverJob?.id ?? null)
      setStep('processing')
      startPolling(wantCv, wantCover, tailorJob?.id ?? null, coverJob?.id ?? null)
    } catch (err: unknown) {
      const detail = (err as AxiosError<{ detail: string }>)?.response?.data?.detail
      toast.error(detail || 'Failed to start')
    } finally {
      setSubmitting(false)
    }
  }

  function toggleSection(id: string) {
    setAcceptedIds((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function editSection(id: string, text: string) {
    setEditedContent((prev) => {
      const next = new Map(prev)
      next.set(id, text)
      return next
    })
  }

  function moveSection(id: string, direction: -1 | 1) {
    setSectionOrder((prev) => {
      const idx = prev.indexOf(id)
      if (idx < 0) return prev
      const targetIdx = idx + direction
      if (targetIdx < 0 || targetIdx >= prev.length) return prev
      const next = [...prev]
      next[idx] = next[targetIdx]
      next[targetIdx] = id
      return next
    })
  }

  async function handleSave() {
    setSaving(true)
    try {
      if (wantCv && tailorJobId && preview) {
        const overrides: Record<string, string> = {}
        for (const [sid, text] of editedContent) overrides[sid] = text
        const result = await tailorApi.save(
          tailorJobId,
          acceptedIds.size === preview.sections.length ? null : [...acceptedIds],
          cvTitle || undefined,
          Object.keys(overrides).length > 0 ? overrides : undefined,
          sectionOrder.length > 0 ? sectionOrder : undefined,
          templateId,
        )
        setSavedCvId(result.cv_id)
        setSavedCvTitle(result.title)
      }
      if (wantCover && coverJobId) {
        await coverLetterApi.save(coverJobId, coverText, coverTitle || undefined)
        setCoverSaved(true)
        refreshHistory()
      }
      setStep('done')
      toast.success(wantCv && wantCover ? 'CV and cover letter saved' : 'Saved')
      tailorApi.getUsage().then(setTailorUsage).catch(() => undefined)
    } catch (err: unknown) {
      toast.error((err as AxiosError<{ detail: string }>)?.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const fetchPreviewHtml = useCallback(
    async (previewTemplateId: CvTemplateId): Promise<string> => {
      if (!tailorJobId || !preview) throw new Error('No tailoring result to preview')
      const overrides: Record<string, string> = {}
      for (const [sid, text] of editedContent) overrides[sid] = text
      const result = await tailorApi.previewHtml(
        tailorJobId,
        acceptedIds.size === preview.sections.length ? null : [...acceptedIds],
        Object.keys(overrides).length > 0 ? overrides : undefined,
        sectionOrder.length > 0 ? sectionOrder : undefined,
        previewTemplateId,
      )
      return result.html
    },
    [tailorJobId, preview, editedContent, acceptedIds, sectionOrder],
  )

  function handleReset() {
    if (pollRef.current) window.clearInterval(pollRef.current)
    cvReadyRef.current = false
    coverReadyRef.current = false
    setStep('select')
    setTailorJobId(null)
    setPreview(null)
    setAcceptedIds(new Set())
    setEditedContent(new Map())
    setSectionOrder([])
    setCvTitle('')
    setTemplateId(preferredTemplate)
    setSavedCvId(null)
    setSavedCvTitle('')
    setCoverJobId(null)
    setCoverText('')
    setCoverTitle('')
    setCoverSaved(false)
  }

  function handleCopy() {
    navigator.clipboard
      .writeText(coverText)
      .then(() => toast.success('Copied to clipboard'))
      .catch(() => toast.error('Failed to copy'))
  }

  function handleDownloadTxt() {
    const blob = new Blob([coverText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${coverTitle || 'cover-letter'}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function handleDownloadCoverPdf() {
    if (!coverJobId) return
    try {
      await coverLetterApi.download(coverJobId, coverTitle || 'cover-letter', templateId)
    } catch {
      toast.error('Could not download the cover letter PDF')
    }
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

  const selectedCv = cvs.find((cv) => cv.id === selectedCvId)
  const selectedJob = jobs.find((job) => job.id === selectedJobId)
  const jobUrl = rawJob?.url ?? selectedJob?.url ?? null

  async function handleAddApplication() {
    setAddingApplication(true)
    try {
      const application = await createApplication(
        rawJobPostingId
          ? { raw_job_posting_id: rawJobPostingId, status: 'wishlist' }
          : {
              company_name: selectedJob?.company_name,
              job_title: selectedJob?.job_title,
              job_url: selectedJob?.url ?? null,
              status: 'wishlist',
            },
      )
      setApplicationStatus(application.status)
      toast.success('Added to applications')
    } catch {
      toast.error('Could not add to applications')
    } finally {
      setAddingApplication(false)
    }
  }

  const tailorAtLimit = Boolean(
    wantCv && tailorUsage && tailorUsage.daily_limit !== null && tailorUsage.used_today >= tailorUsage.daily_limit,
  )
  const coverAtLimit = Boolean(
    wantCover && coverUsage && coverUsage.daily_limit !== null && coverUsage.used_today >= coverUsage.daily_limit,
  )
  const canSubmit = Boolean(
    selectedCvId &&
      (rawJobPostingId || selectedJobId) &&
      (wantCv || wantCover) &&
      !submitting &&
      !tailorAtLimit &&
      !coverAtLimit,
  )

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-fg">
          <SparklesIcon className="h-7 w-7 text-accent-text" />
          AI Tailor
        </h1>
        <p className="mt-1 text-sm text-fg-subtle">
          Tailor your CV and write a matching cover letter for a job — in one flow. Review, edit, and
          export each as a PDF.
        </p>
      </div>

      {step === 'select' && (
        <div className="space-y-2">
          {wantCv && tailorUsage && <UsageBanner label={tailorUsageLabel(tailorUsage)} resetsAt={tailorUsage.resets_at} />}
          {wantCover && coverUsage && <UsageBanner label={coverUsageLabel(coverUsage)} resetsAt={coverUsage.resets_at} />}
        </div>
      )}

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
              selectedCv={selectedCv}
              selectedJob={selectedJob}
              rawJob={rawJob}
              rawJobPostingId={rawJobPostingId}
              wantCv={wantCv}
              wantCover={wantCover}
              intensity={intensity}
              tone={tone}
              onCvChange={setSelectedCvId}
              onJobChange={setSelectedJobId}
              onWantCvChange={setWantCv}
              onWantCoverChange={setWantCover}
              onIntensityChange={setIntensity}
              onToneChange={setTone}
              onSubmit={handleSubmit}
              canSubmit={canSubmit}
              submitting={submitting}
              tailorAtLimit={tailorAtLimit}
              coverAtLimit={coverAtLimit}
            />
          )}

          {step === 'processing' && <ProcessingStep wantCv={wantCv} wantCover={wantCover} />}

          {step === 'review' && (
            <ReviewStep
              wantCv={wantCv}
              wantCover={wantCover}
              preview={preview}
              acceptedIds={acceptedIds}
              editedContent={editedContent}
              sectionOrder={sectionOrder}
              cvTitle={cvTitle}
              templateId={templateId}
              coverText={coverText}
              coverTitle={coverTitle}
              saving={saving}
              onToggle={toggleSection}
              onEditSection={editSection}
              onMove={moveSection}
              onCvTitleChange={setCvTitle}
              onTemplateChange={setTemplateId}
              onFetchPreviewHtml={fetchPreviewHtml}
              onCoverTextChange={setCoverText}
              onCoverTitleChange={setCoverTitle}
              onCopy={handleCopy}
              onSave={handleSave}
              onBack={handleReset}
            />
          )}

          {step === 'done' && (
            <DoneStep
              wantCv={wantCv}
              wantCover={wantCover}
              savedCvId={savedCvId}
              savedCvTitle={savedCvTitle}
              coverText={coverText}
              coverTitle={coverTitle}
              coverSaved={coverSaved}
              jobUrl={jobUrl}
              applicationStatus={applicationStatus}
              addingApplication={addingApplication}
              onAddToApplications={handleAddApplication}
              onCopy={handleCopy}
              onDownloadCoverPdf={handleDownloadCoverPdf}
              onDownloadTxt={handleDownloadTxt}
              onReset={handleReset}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {(history.length > 0 || historyLoading) && (
        <HistorySection history={history} loading={historyLoading} onDelete={handleDelete} />
      )}
    </div>
  )
}

function tailorUsageLabel(usage: TailorUsage): string {
  return usage.daily_limit === null
    ? `${usage.used_today} CV tailoring runs used today. Admin access has no daily limit.`
    : `${usage.used_today} of ${usage.daily_limit} CV tailoring runs used today.`
}

function coverUsageLabel(usage: CoverLetterUsage): string {
  return usage.daily_limit === null
    ? `${usage.used_today} cover letters used today. Admin access has no daily limit.`
    : `${usage.used_today} of ${usage.daily_limit} cover letters used today.`
}

function UsageBanner({ label, resetsAt }: { label: string; resetsAt: string }) {
  const resetTime = new Date(resetsAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return (
    <div className="rounded-xl border border-brand-100 bg-primary-900/20 px-4 py-3">
      <p className="text-sm font-medium text-fg">{label}</p>
      <p className="mt-0.5 text-xs text-accent-text">Resets at {resetTime} UTC.</p>
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
  rawJob: DiscoveredJobDetail | null
  rawJobPostingId: string | undefined
  wantCv: boolean
  wantCover: boolean
  intensity: TailorIntensity
  tone: CoverLetterTone
  onCvChange: (value: string) => void
  onJobChange: (value: string) => void
  onWantCvChange: (value: boolean) => void
  onWantCoverChange: (value: boolean) => void
  onIntensityChange: (value: TailorIntensity) => void
  onToneChange: (value: CoverLetterTone) => void
  onSubmit: () => void
  canSubmit: boolean
  submitting: boolean
  tailorAtLimit: boolean
  coverAtLimit: boolean
}

function SelectStep({
  cvs,
  jobs,
  loading,
  selectedCvId,
  selectedJobId,
  selectedCv,
  selectedJob,
  rawJob,
  rawJobPostingId,
  wantCv,
  wantCover,
  intensity,
  tone,
  onCvChange,
  onJobChange,
  onWantCvChange,
  onWantCoverChange,
  onIntensityChange,
  onToneChange,
  onSubmit,
  canSubmit,
  submitting,
  tailorAtLimit,
  coverAtLimit,
}: SelectStepProps) {
  const submitLabel =
    wantCv && wantCover
      ? 'Tailor CV & write cover letter'
      : wantCv
        ? 'Tailor CV'
        : 'Write cover letter'

  return (
    <div className="space-y-6 rounded-2xl border border-line bg-surface p-6">
      <div>
        <h2 className="text-sm font-semibold text-fg-muted">Select source CV and target job</h2>
        <p className="mt-1 text-xs text-fg-subtle">
          Your original CV stays unchanged. A tailored copy and cover letter are created only after
          you save.
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
        {rawJobPostingId ? (
          <div className="rounded-lg border border-brand-100 bg-primary-900/20 px-3 py-2.5">
            <p className="text-xs font-medium uppercase tracking-wide text-accent-text">Target job</p>
            <p className="mt-1 text-sm font-semibold text-fg">
              {rawJob ? `${rawJob.title} @ ${rawJob.company}` : 'Loading discovered job'}
            </p>
          </div>
        ) : (
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
        )}
      </div>

      {(selectedCv || selectedJob) && (
        <div className="flex flex-wrap gap-2">
          {selectedCv && <Pill>{selectedCv.title}</Pill>}
          {rawJob && <Pill>{`${rawJob.title} @ ${rawJob.company}`}</Pill>}
          {!rawJob && selectedJob && <Pill>{`${selectedJob.job_title} @ ${selectedJob.company_name}`}</Pill>}
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-fg-muted">What should we create?</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ToggleCard
            icon={SparklesIcon}
            title="Tailor CV"
            description="Rewrite your CV section by section for this job."
            checked={wantCv}
            onChange={onWantCvChange}
          />
          <ToggleCard
            icon={PencilSquareIcon}
            title="Write cover letter"
            description="Generate a matching cover letter you can edit and export."
            checked={wantCover}
            onChange={onWantCoverChange}
          />
        </div>
        {!wantCv && !wantCover && (
          <p className="text-sm text-chip-danger-fg">Choose at least one to continue.</p>
        )}
      </div>

      {wantCv && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-fg-muted">Tailoring intensity</h3>
          <IntensitySelector value={intensity} onChange={onIntensityChange} />
        </div>
      )}

      {wantCover && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-fg-muted">Cover letter tone</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {TONE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onToneChange(option.value)}
                className={`rounded-xl border p-3 text-left transition-colors ${
                  tone === option.value
                    ? 'border-primary-500/50 bg-primary-900/20 ring-1 ring-brand-400'
                    : 'border-line bg-surface hover:border-line-strong'
                }`}
              >
                <p className="text-sm font-semibold text-fg">{option.label}</p>
                <p className="mt-0.5 text-xs text-fg-subtle">{option.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={onSubmit}
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? (
          <>
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            Starting…
          </>
        ) : (
          <>
            <SparklesIcon className="h-4 w-4" />
            {submitLabel}
          </>
        )}
      </button>

      {(tailorAtLimit || coverAtLimit) && (
        <p className="text-sm text-chip-danger-fg">
          {tailorAtLimit && coverAtLimit
            ? 'Daily limits reached for both. Try again after the reset time or upgrade to premium.'
            : tailorAtLimit
              ? 'Daily CV tailoring limit reached. Turn off "Tailor CV" or try again after the reset time.'
              : 'Daily cover letter limit reached. Turn off "Write cover letter" or try again after the reset time.'}
        </p>
      )}
    </div>
  )
}

function ToggleCard({
  icon: Icon,
  title,
  description,
  checked,
  onChange,
}: {
  icon: typeof SparklesIcon
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      className={`flex items-start gap-3 rounded-xl border-2 p-4 text-left transition-colors ${
        checked ? 'border-brand-500 bg-primary-900/20' : 'border-line bg-surface hover:border-line-strong'
      }`}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${checked ? 'text-accent-text' : 'text-fg-subtle'}`} />
      <span className="min-w-0">
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-fg">{title}</span>
          {checked && <CheckCircleIcon className="h-4 w-4 text-accent-text" />}
        </span>
        <span className="mt-0.5 block text-xs leading-5 text-fg-subtle">{description}</span>
      </span>
    </button>
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
      <label className="text-xs font-medium uppercase tracking-wide text-fg-muted">{label}</label>
      {loading ? (
        <div className="h-10 animate-pulse rounded-lg bg-track" />
      ) : options.length === 0 ? (
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-line-strong px-3 py-2.5 text-sm text-fg-subtle">
          {emptyMessage}
          <Link to={emptyHref} className="text-accent-text hover:underline">
            {emptyLinkLabel}
          </Link>
        </div>
      ) : (
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
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
    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-900/20 px-2.5 py-1 text-xs font-medium text-accent-text">
      <CheckCircleIcon className="h-3.5 w-3.5" />
      {children}
    </span>
  )
}

function ProcessingStep({ wantCv, wantCover }: { wantCv: boolean; wantCover: boolean }) {
  const heading =
    wantCv && wantCover
      ? 'Tailoring your CV and writing your cover letter'
      : wantCv
        ? 'Tailoring your CV'
        : 'Writing your cover letter'

  const [activeStep, setActiveStep] = useState(0)
  const steps = [
    { label: 'Parsing CV', sublabel: 'Extracting your experience' },
    { label: 'Detecting language', sublabel: 'Matching the output language' },
    { label: 'Analysing job description', sublabel: 'Identifying key requirements' },
    { label: 'Generating', sublabel: 'AI is writing your documents' },
    { label: 'Finalising', sublabel: 'Preparing your preview' },
  ]

  useEffect(() => {
    const delays = [2000, 4000, 8000, 20000]
    const timers = delays.map((delay, index) =>
      window.setTimeout(() => setActiveStep(index + 1), delay),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className="rounded-2xl border border-line bg-surface p-8">
      <h2 className="mb-6 text-base font-semibold text-fg">{heading}</h2>
      <ol className="flex flex-col gap-4 sm:flex-row sm:items-start">
        {steps.map((s, index) => {
          const done = index < activeStep
          const active = index === activeStep
          return (
            <li key={s.label} className="flex min-w-0 items-start gap-3 sm:flex-1">
              <div
                className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-colors ${
                  done ? 'bg-green-500' : active ? 'animate-pulse bg-brand-500' : 'bg-track'
                }`}
              >
                {done && (
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <div>
                <p className={`text-sm font-medium ${active ? 'text-fg' : 'text-fg-subtle'}`}>{s.label}</p>
                {active && <p className="mt-0.5 text-xs text-fg-subtle">{s.sublabel}</p>}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

interface ReviewStepProps {
  wantCv: boolean
  wantCover: boolean
  preview: TailorPreview | null
  acceptedIds: Set<string>
  editedContent: Map<string, string>
  sectionOrder: string[]
  cvTitle: string
  templateId: CvTemplateId
  coverText: string
  coverTitle: string
  saving: boolean
  onToggle: (sectionId: string) => void
  onEditSection: (id: string, text: string) => void
  onMove: (id: string, direction: -1 | 1) => void
  onCvTitleChange: (value: string) => void
  onTemplateChange: (value: CvTemplateId) => void
  onFetchPreviewHtml: (templateId: CvTemplateId) => Promise<string>
  onCoverTextChange: (value: string) => void
  onCoverTitleChange: (value: string) => void
  onCopy: () => void
  onSave: () => void
  onBack: () => void
}

function ReviewStep({
  wantCv,
  wantCover,
  preview,
  acceptedIds,
  editedContent,
  sectionOrder,
  cvTitle,
  templateId,
  coverText,
  coverTitle,
  saving,
  onToggle,
  onEditSection,
  onMove,
  onCvTitleChange,
  onTemplateChange,
  onFetchPreviewHtml,
  onCoverTextChange,
  onCoverTitleChange,
  onCopy,
  onSave,
  onBack,
}: ReviewStepProps) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const sectionMap = preview ? new Map(preview.sections.map((s) => [s.section_id, s])) : new Map()
  const orderedSections = sectionOrder
    .map((id) => sectionMap.get(id))
    .filter((s): s is NonNullable<typeof s> => s !== undefined)
  const wordCount = coverText.trim() ? coverText.trim().split(/\s+/).length : 0

  return (
    <div className="space-y-6">
      {wantCv && preview && (
        <div className="space-y-5">
          <TailorSummary meta={preview.meta} />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-fg">Review CV section changes</h2>
              <p className="mt-1 text-sm text-fg-subtle">
                Accept, edit, or reorder sections. Rejected sections keep the original text.
              </p>
            </div>
            <div className="text-sm text-fg-subtle">
              {acceptedIds.size} of {preview.sections.length} accepted
            </div>
          </div>

          <div className="space-y-4">
            {orderedSections.map((section, idx) => (
              <SectionDiff
                key={section.section_id}
                section={section}
                accepted={acceptedIds.has(section.section_id)}
                onToggle={() => onToggle(section.section_id)}
                editedText={editedContent.get(section.section_id)}
                onEdit={(text) => onEditSection(section.section_id, text)}
                onMoveUp={() => onMove(section.section_id, -1)}
                onMoveDown={() => onMove(section.section_id, 1)}
                isFirst={idx === 0}
                isLast={idx === orderedSections.length - 1}
              />
            ))}
          </div>

          <div className="rounded-2xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-fg">PDF template</h3>
                <p className="mb-3 mt-0.5 text-xs text-fg-subtle">
                  The design applied to the saved CV and the cover letter PDF.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPreviewOpen(true)}
                className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-sm font-semibold text-fg-muted transition hover:bg-surface-strong hover:text-fg"
              >
                <EyeIcon className="h-4 w-4" />
                Preview
              </button>
            </div>
            <TemplatePicker value={templateId} onChange={onTemplateChange} />
            <TemplatePreviewModal
              open={previewOpen}
              templateId={templateId}
              onClose={() => setPreviewOpen(false)}
              onTemplateChange={onTemplateChange}
              fetchHtml={onFetchPreviewHtml}
            />
          </div>

          <div className="rounded-2xl border border-line bg-surface p-5">
            <label className="text-xs font-medium uppercase tracking-wide text-fg-muted">
              Saved CV title
            </label>
            <input
              value={cvTitle}
              onChange={(event) => onCvTitleChange(event.target.value)}
              placeholder="Tailored CV"
              className="mt-1.5 w-full rounded-lg border border-line px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
      )}

      {wantCover && (
        <div className="space-y-4 rounded-2xl border border-line bg-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-fg">Edit your cover letter</h2>
              <p className="mt-0.5 text-xs text-fg-subtle">
                Review and refine before saving. Changes are only saved when you click Save.
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-surface px-2.5 py-0.5 text-xs font-medium text-fg-subtle">
              {wordCount} words
            </span>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-fg-muted">Cover letter title (optional)</label>
            <input
              type="text"
              className="input w-full"
              placeholder="e.g. Cover letter for Spotify"
              value={coverTitle}
              onChange={(e) => onCoverTitleChange(e.target.value)}
            />
          </div>

          <textarea
            className="input min-h-[400px] w-full resize-y font-mono text-sm leading-relaxed"
            value={coverText}
            onChange={(e) => onCoverTextChange(e.target.value)}
            spellCheck
          />

          <button
            type="button"
            onClick={onCopy}
            className="inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 py-2.5 text-sm font-medium text-fg-muted hover:bg-surface-strong"
          >
            <ClipboardDocumentIcon className="h-4 w-4" />
            Copy text
          </button>
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50"
        >
          Start over
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saving || (wantCover && !coverText.trim())}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {saving && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
          {wantCv && wantCover ? 'Save CV & cover letter' : wantCv ? 'Save tailored PDF' : 'Save cover letter'}
        </button>
      </div>
    </div>
  )
}

interface DoneStepProps {
  wantCv: boolean
  wantCover: boolean
  savedCvId: string | null
  savedCvTitle: string
  coverText: string
  coverTitle: string
  coverSaved: boolean
  jobUrl: string | null
  applicationStatus: string | null
  addingApplication: boolean
  onAddToApplications: () => void
  onCopy: () => void
  onDownloadCoverPdf: () => void
  onDownloadTxt: () => void
  onReset: () => void
}

function DoneStep({
  wantCv,
  wantCover,
  savedCvId,
  savedCvTitle,
  coverText,
  coverTitle,
  coverSaved,
  jobUrl,
  applicationStatus,
  addingApplication,
  onAddToApplications,
  onCopy,
  onDownloadCoverPdf,
  onDownloadTxt,
  onReset,
}: DoneStepProps) {
  const [downloadingCv, setDownloadingCv] = useState(false)

  async function handleDownloadCv() {
    if (!savedCvId) return
    setDownloadingCv(true)
    try {
      await cvApi.download(savedCvId, savedCvTitle ? `${savedCvTitle}.pdf` : 'tailored-cv.pdf')
    } catch {
      toast.error('Could not download the tailored CV')
    } finally {
      setDownloadingCv(false)
    }
  }

  return (
    <div className="space-y-6 rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-chip-success">
          <CheckCircleIcon className="h-6 w-6 text-chip-success-fg" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-fg">
            {wantCv && wantCover ? 'CV and cover letter saved' : wantCv ? 'Tailored CV saved' : 'Cover letter saved'}
          </h2>
          <p className="mt-0.5 text-sm text-fg-subtle">
            Your original CV stays unchanged. Download or copy your documents below.
          </p>
        </div>
      </div>

      {wantCv && savedCvId && (
        <div className="space-y-2 rounded-xl border border-line p-4">
          <p className="text-sm font-semibold text-fg">Tailored CV</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleDownloadCv}
              disabled={downloadingCv}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {downloadingCv ? (
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowDownTrayIcon className="h-4 w-4" />
              )}
              Download PDF
            </button>
            <Link
              to="/cvs"
              className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
            >
              View in My CVs
            </Link>
          </div>
        </div>
      )}

      {wantCover && coverSaved && (
        <div className="space-y-3 rounded-xl border border-line p-4">
          <p className="text-sm font-semibold text-fg">Cover letter{coverTitle ? ` — ${coverTitle}` : ''}</p>
          <pre className="max-h-[320px] overflow-y-auto whitespace-pre-wrap rounded-lg bg-surface p-3 text-sm leading-relaxed text-fg-muted">
            {coverText}
          </pre>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onDownloadCoverPdf}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Download PDF
            </button>
            <button
              type="button"
              onClick={onCopy}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-strong"
            >
              <ClipboardDocumentIcon className="h-4 w-4" />
              Copy text
            </button>
            <button
              type="button"
              onClick={onDownloadTxt}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-strong"
            >
              <DocumentTextIcon className="h-4 w-4" />
              Download .txt
            </button>
          </div>
        </div>
      )}

      {/* Apply nudge — close the loop from tailoring to applying. */}
      <div className="space-y-3 rounded-xl border border-primary-600/30 bg-primary-900/20 p-4">
        <p className="text-sm font-semibold text-fg">Ready to apply?</p>
        <div className="flex flex-wrap items-center gap-2">
          {jobUrl && (
            <a
              href={jobUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              Apply now
            </a>
          )}
          {applicationStatus ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-lg bg-chip-success px-3 py-1.5 text-sm font-medium text-chip-success-fg">
                <BriefcaseIcon className="h-4 w-4" />
                {applicationStatus.replace('_', ' ')}
              </span>
              <Link
                to="/applications"
                className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
              >
                View in Applications
              </Link>
            </div>
          ) : (
            <button
              type="button"
              onClick={onAddToApplications}
              disabled={addingApplication}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50"
            >
              <BriefcaseIcon className="h-4 w-4" />
              {addingApplication ? 'Adding…' : 'Add to Applications'}
            </button>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="inline-flex items-center gap-2 rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
      >
        <SparklesIcon className="h-4 w-4" />
        Start another
      </button>
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
    <div className="rounded-2xl border border-line bg-surface">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-6 py-4 text-sm font-semibold text-fg-muted"
      >
        <span>Cover letter history ({history.length})</span>
        <span className="text-fg-subtle">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="divide-y divide-line border-t border-line">
          {loading ? (
            <div className="px-6 py-4 text-sm text-fg-subtle">Loading…</div>
          ) : history.length === 0 ? (
            <div className="px-6 py-4 text-sm text-fg-subtle">No cover letters yet.</div>
          ) : (
            history.map((job) => (
              <div key={job.id} className="flex items-center justify-between gap-4 px-6 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-fg">
                    {job.title || 'Untitled cover letter'}
                  </p>
                  <p className="mt-0.5 text-xs text-fg-subtle">
                    {job.tone} · {job.status} · {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onDelete(job.id)}
                  className="shrink-0 rounded-lg p-1.5 text-chip-danger-fg hover:bg-chip-danger"
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
