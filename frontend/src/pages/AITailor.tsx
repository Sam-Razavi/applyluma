import { useCallback, useEffect, useRef, useState } from 'react'
import type { AxiosError } from 'axios'
import { SparklesIcon } from '@heroicons/react/24/outline'
import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
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
import { SelectStep } from '../components/tailor/steps/SelectStep'
import { ProcessingStep } from '../components/tailor/steps/ProcessingStep'
import { ReviewStep } from '../components/tailor/steps/ReviewStep'
import { DoneStep } from '../components/tailor/steps/DoneStep'
import { HistorySection } from '../components/tailor/steps/HistorySection'

type Step = 'select' | 'processing' | 'review' | 'done'

const POLL_INTERVAL_MS = 2500

const TEMPLATE_IDS: CvTemplateId[] = ['nordic', 'classic', 'modern', 'executive', 'atlas', 'compact']

/** Narrow the wire value (users.preferred_template) to a known template id. */
function resolveTemplate(value?: string | null): CvTemplateId {
  return TEMPLATE_IDS.includes(value as CvTemplateId) ? (value as CvTemplateId) : 'nordic'
}

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

    async function poll() {
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
    }

    void poll()
    pollRef.current = window.setInterval(poll, POLL_INTERVAL_MS)
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
