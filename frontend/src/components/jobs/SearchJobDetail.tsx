import { useEffect, useState } from 'react'
import {
  ArrowTopRightOnSquareIcon,
  BookmarkIcon as BookmarkOutline,
  BriefcaseIcon,
  SparklesIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { BookmarkIcon as BookmarkSolid } from '@heroicons/react/24/solid'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import SkillsBreakdown from '../discover/SkillsBreakdown'
import JobDescriptionDisplay from '../common/JobDescriptionDisplay'
import { useUsageStore, usageHint } from '../../stores/usage'
import type { AdzunaJobResult, AnalyzeTextResponse } from '../../services/jobSearchApi'
import { analyzeJobText, bookmarkSearchJob } from '../../services/jobSearchApi'
import type { ApplicationCreate } from '../../types/application'

interface Props {
  job: AdzunaJobResult | null
  onClose: () => void
  onTrack: (data: Partial<ApplicationCreate>) => void
}

function Pill({ text, color }: { text: string; color: string }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{text}</span>
  )
}


export default function SearchJobDetail({ job, onClose, onTrack }: Props) {
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState<AnalyzeTextResponse | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [bookmarking, setBookmarking] = useState(false)
  const [rawJobPostingId, setRawJobPostingId] = useState<string | null>(null)
  const [addingApplication, setAddingApplication] = useState(false)
  const tailorUsage = useUsageStore((s) => s.tailorUsage)
  const coverUsage = useUsageStore((s) => s.coverUsage)
  const loadUsage = useUsageStore((s) => s.loadUsage)

  useEffect(() => {
    void loadUsage()
  }, [loadUsage])

  useEffect(() => {
    if (!job) {
      setAnalysis(null)
      setIsSaved(false)
      setRawJobPostingId(null)
      return
    }
    setAnalyzing(true)
    analyzeJobText(job.description)
      .then(setAnalysis)
      .catch(() => setAnalysis(null))
      .finally(() => setAnalyzing(false))
  }, [job])

  if (!job) return null

  const sourceName = job.source === 'platsbanken' ? 'Platsbanken' : 'Adzuna'

  async function handleSave() {
    if (!job || bookmarking) return
    setBookmarking(true)
    try {
      const result = await bookmarkSearchJob(job)
      setIsSaved(true)
      setRawJobPostingId(result.source_raw_job_posting_id)
      toast.success('Job saved!')
    } catch {
      toast.error('Failed to save job')
    } finally {
      setBookmarking(false)
    }
  }

  async function handleTailor() {
    if (!job) return
    let postingId = rawJobPostingId
    if (!postingId) {
      setBookmarking(true)
      try {
        const result = await bookmarkSearchJob(job)
        setIsSaved(true)
        postingId = result.source_raw_job_posting_id
        setRawJobPostingId(postingId)
      } catch {
        toast.error('Failed to save job')
        setBookmarking(false)
        return
      } finally {
        setBookmarking(false)
      }
    }
    if (!postingId) {
      toast.error('Could not resolve job reference')
      return
    }
    navigate('/ai-tailor', {
      state: {
        rawJobPostingId: postingId,
        jobTitle: job.title,
        company: job.company_name,
      },
    })
  }

  function handleTrack() {
    if (!job) return
    setAddingApplication(true)
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
    })
    setAddingApplication(false)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center px-4 pt-4 pb-24 sm:p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl overflow-y-auto rounded-2xl border border-line shadow-2xl"
        style={{
          maxHeight: 'min(calc(100dvh - 7rem), 90vh)',
          background: 'var(--nav-bg)',
          backdropFilter: 'blur(14px)',
          WebkitBackdropFilter: 'blur(14px)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-fg-subtle hover:bg-surface-strong hover:text-fg-muted"
          aria-label="Close"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>

        <div className="p-6 space-y-5">
          {/* Header */}
          <div className="pr-8 space-y-1">
            <h2 className="text-xl font-bold text-fg">{job.title}</h2>
            <p className="text-sm text-fg-muted">{job.company_name}</p>
            <div className="flex flex-wrap gap-2 pt-1">
              {job.location && (
                <Pill text={job.location} color="bg-surface text-fg-muted" />
              )}
              {job.contract_type && (
                <Pill text={job.contract_type} color="bg-surface text-fg-muted" />
              )}
              <Pill text={sourceName} color="bg-[rgba(139,92,246,0.15)] text-violet-300" />
            </div>
          </div>

          {/* Skills analysis */}
          {analyzing ? (
            <div className="rounded-xl border border-line bg-surface p-4">
              <div className="h-4 w-32 animate-pulse rounded bg-track mb-3" />
              <div className="flex flex-wrap gap-1.5">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-6 w-16 animate-pulse rounded-full bg-track" />
                ))}
              </div>
            </div>
          ) : analysis ? (
            <SkillsBreakdown
              matchedSkills={analysis.matched_skills}
              missingSkills={analysis.missing_skills}
            />
          ) : null}

          {/* Description */}
          {job.description && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-fg">Job description</h3>
              <JobDescriptionDisplay raw={job.description} />
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:gap-3">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={bookmarking || isSaved}
              className={`flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors sm:w-auto ${
                isSaved
                  ? 'bg-primary-100 text-accent-text'
                  : 'border border-line-strong text-fg-muted hover:bg-surface-strong'
              } disabled:opacity-50`}
            >
              {isSaved ? (
                <>
                  <BookmarkSolid className="h-4 w-4" />
                  Saved
                </>
              ) : (
                <>
                  <BookmarkOutline className="h-4 w-4" />
                  {bookmarking ? 'Saving...' : 'Save job'}
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => void handleTailor()}
              disabled={bookmarking}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-2.5 text-sm font-medium text-accent-text transition-colors hover:bg-brand-100 disabled:opacity-50 sm:w-auto"
            >
              <SparklesIcon className="h-4 w-4" />
              Tailor CV + Cover Letter
            </button>
            <button
              type="button"
              onClick={handleTrack}
              disabled={addingApplication}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-line-strong px-4 py-2.5 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50 sm:w-auto"
            >
              <BriefcaseIcon className="h-4 w-4" />
              Add to Applications
            </button>
            <a
              href={job.redirect_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 sm:w-auto"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              Apply now
            </a>
          </div>

          {usageHint(tailorUsage, coverUsage) && (
            <p className="text-xs text-chip-danger-fg">{usageHint(tailorUsage, coverUsage)}</p>
          )}
        </div>
      </div>
    </div>
  )
}
