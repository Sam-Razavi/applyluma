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
import type { DiscoveredJobDetail } from '../../types/jobDiscovery'
import { SOURCE_LABELS } from '../../types/jobDiscovery'
import JobDescriptionDisplay from '../common/JobDescriptionDisplay'
import { fetchJobDetail } from '../../services/jobDiscoveryApi'
import { createApplication } from '../../services/applicationsApi'
import { useUsageStore, usageHint } from '../../stores/usage'
import ScoreBreakdown from './ScoreBreakdown'
import SkillsBreakdown from './SkillsBreakdown'

interface Props {
  jobId: string | null
  isSaved: boolean
  onClose: () => void
  onSave: (jobId: string) => void
  onApplicationCreated?: (jobId: string, applicationId: string, status: string) => void
}

function Pill({ text, color }: { text: string; color: string }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{text}</span>
  )
}

export default function JobDetail({
  jobId,
  isSaved,
  onClose,
  onSave,
  onApplicationCreated,
}: Props) {
  const navigate = useNavigate()
  const [job, setJob] = useState<DiscoveredJobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [addingApplication, setAddingApplication] = useState(false)
  const tailorUsage = useUsageStore((s) => s.tailorUsage)
  const coverUsage = useUsageStore((s) => s.coverUsage)
  const loadUsage = useUsageStore((s) => s.loadUsage)

  useEffect(() => {
    void loadUsage()
  }, [loadUsage])

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      return
    }
    setLoading(true)
    setError(null)
    fetchJobDetail(jobId)
      .then(setJob)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load job'))
      .finally(() => setLoading(false))
  }, [jobId])

  if (!jobId) return null

  async function handleAddApplication() {
    if (!job) return
    setAddingApplication(true)
    try {
      const application = await createApplication({
        raw_job_posting_id: job.job_id,
        status: 'wishlist',
      })
      setJob({ ...job, application_id: application.id, application_status: application.status })
      onApplicationCreated?.(job.job_id, application.id, application.status)
      toast.success('Added to applications')
    } catch {
      toast.error('Failed to add application')
    } finally {
      setAddingApplication(false)
    }
  }

  function handleTailor() {
    if (!job) return
    navigate('/ai-tailor', {
      state: {
        rawJobPostingId: job.job_id,
        jobTitle: job.title,
        company: job.company,
      },
    })
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
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-fg-subtle hover:bg-surface-strong hover:text-fg-muted"
          aria-label="Close"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>

        {loading && (
          <div className="flex items-center justify-center p-16">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          </div>
        )}

        {error && !loading && (
          <div className="p-8 text-center text-sm text-chip-danger-fg">{error}</div>
        )}

        {job && !loading && (
          <div className="p-6 space-y-5">
            {/* Header */}
            <div className="pr-8 space-y-1">
              <h2 className="text-xl font-bold text-fg">{job.title}</h2>
              <p className="text-sm text-fg-muted">{job.company}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                {job.location && (
                  <Pill text={job.location} color="bg-surface text-fg-muted" />
                )}
                {job.remote_allowed && (
                  <Pill text="Remote" color="bg-chip-accent text-accent-text" />
                )}
                {job.employment_type && (
                  <Pill
                    text={job.employment_type.replace('_', ' ')}
                    color="bg-surface text-fg-muted"
                  />
                )}
                <Pill
                  text={SOURCE_LABELS[job.source] ?? job.source}
                  color="bg-surface text-fg-subtle"
                />
              </div>
            </div>

            {/* Match score summary */}
            {job.match_score !== null && (
              <div className="rounded-xl border border-primary-100 bg-primary-900/20 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-primary-800">Match score</span>
                  <span
                    className="text-lg font-bold text-accent-text"
                    title="Weights: skills 40%, experience 30%, salary 15%, education 10%, location 5%"
                  >
                    {Math.round(job.match_score)}%
                  </span>
                </div>
              </div>
            )}

            <ScoreBreakdown
              skillsMatch={job.skills_match}
              experienceMatch={job.experience_match}
              salaryMatchScore={job.salary_match_score}
              educationMatch={job.education_match}
              locationMatch={job.location_match}
              explanation={job.explanation}
            />

            <SkillsBreakdown
              matchedSkills={job.matched_skills}
              missingSkills={job.missing_skills}
            />

            {/* Description */}
            {job.description && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-fg">Job description</h3>
                <JobDescriptionDisplay raw={job.description} />
              </div>
            )}

            {/* Already-tailored hint */}
            {(job.tailored_cv_id || job.cover_letter_job_id) && (
              <div className="flex flex-col gap-1.5 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <span className="font-medium text-accent-text">
                  You've already tailored this job.
                </span>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {job.tailored_cv_id && (
                    <button
                      type="button"
                      onClick={() => navigate('/cvs')}
                      className="font-medium text-accent-text underline-offset-2 hover:underline"
                    >
                      View tailored CV
                    </button>
                  )}
                  {job.cover_letter_job_id && (
                    <button
                      type="button"
                      onClick={() => navigate('/ai-tailor')}
                      className="font-medium text-accent-text underline-offset-2 hover:underline"
                    >
                      View cover letter
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:gap-3">
              <button
                type="button"
                onClick={() => onSave(job.job_id)}
                className={`flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors sm:w-auto ${
                  isSaved
                    ? 'bg-primary-100 text-accent-text hover:bg-primary-200'
                    : 'border border-line-strong text-fg-muted hover:bg-surface-strong'
                }`}
              >
                {isSaved ? (
                  <>
                    <BookmarkSolid className="h-4 w-4" />
                    Saved
                  </>
                ) : (
                  <>
                    <BookmarkOutline className="h-4 w-4" />
                    Save job
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleTailor}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-2.5 text-sm font-medium text-accent-text transition-colors hover:bg-brand-100 sm:w-auto"
              >
                <SparklesIcon className="h-4 w-4" />
                Tailor CV + Cover Letter
              </button>
              {job.application_status ? (
                <span className="flex w-full items-center justify-center gap-2 rounded-xl bg-chip-success px-4 py-2.5 text-sm font-medium text-chip-success-fg sm:w-auto">
                  <BriefcaseIcon className="h-4 w-4" />
                  {job.application_status.replace('_', ' ')}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => void handleAddApplication()}
                  disabled={addingApplication}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-line-strong px-4 py-2.5 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50 sm:w-auto"
                >
                  <BriefcaseIcon className="h-4 w-4" />
                  {addingApplication ? 'Adding' : 'Add to Applications'}
                </button>
              )}
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 sm:w-auto"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                Apply now
              </a>
            </div>

            {/* Daily-limit hint */}
            {usageHint(tailorUsage, coverUsage) && (
              <p className="text-xs text-chip-danger-fg">{usageHint(tailorUsage, coverUsage)}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
