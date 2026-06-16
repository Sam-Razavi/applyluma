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
import { fetchJobDetail } from '../../services/jobDiscoveryApi'
import { createApplication } from '../../services/applicationsApi'
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
    navigate('/ai-tailor', { state: { rawJobPostingId: job.job_id } })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center px-4 pt-4 pb-24 sm:p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/[0.08] shadow-2xl"
        style={{
          maxHeight: 'min(calc(100dvh - 7rem), 90vh)',
          background: 'rgba(8,14,18,0.92)',
          backdropFilter: 'blur(14px)',
          WebkitBackdropFilter: 'blur(14px)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-white/30 hover:bg-white/[0.06] hover:text-white/55"
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
          <div className="p-8 text-center text-sm text-red-300">{error}</div>
        )}

        {job && !loading && (
          <div className="p-6 space-y-5">
            {/* Header */}
            <div className="pr-8 space-y-1">
              <h2 className="text-xl font-bold text-white/90">{job.title}</h2>
              <p className="text-sm text-white/55">{job.company}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                {job.location && (
                  <Pill text={job.location} color="bg-white/[0.04] text-white/55" />
                )}
                {job.remote_allowed && (
                  <Pill text="Remote" color="bg-[rgba(8,145,178,0.15)] text-cyan-300" />
                )}
                {job.employment_type && (
                  <Pill
                    text={job.employment_type.replace('_', ' ')}
                    color="bg-white/[0.04] text-white/55"
                  />
                )}
                <Pill
                  text={SOURCE_LABELS[job.source] ?? job.source}
                  color="bg-white/[0.04] text-white/30"
                />
              </div>
            </div>

            {/* Match score summary */}
            {job.match_score !== null && (
              <div className="rounded-xl border border-primary-100 bg-primary-900/20 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-primary-800">Match score</span>
                  <span
                    className="text-lg font-bold text-primary-400"
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
                <h3 className="mb-2 text-sm font-semibold text-white/90">Job description</h3>
                <div className="prose prose-sm max-w-none text-white/55 whitespace-pre-line text-sm leading-relaxed">
                  {job.description}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-2 border-t border-white/10 pt-4 sm:flex-row sm:gap-3">
              <button
                type="button"
                onClick={() => onSave(job.job_id)}
                className={`flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors sm:w-auto ${
                  isSaved
                    ? 'bg-primary-100 text-primary-400 hover:bg-primary-200'
                    : 'border border-white/15 text-white/55 hover:bg-white/[0.04]'
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
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-2.5 text-sm font-medium text-primary-400 transition-colors hover:bg-brand-100 sm:w-auto"
              >
                <SparklesIcon className="h-4 w-4" />
                Tailor CV
              </button>
              {job.application_status ? (
                <span className="flex w-full items-center justify-center gap-2 rounded-xl bg-[rgba(52,195,143,0.14)] px-4 py-2.5 text-sm font-medium text-emerald-300 sm:w-auto">
                  <BriefcaseIcon className="h-4 w-4" />
                  {job.application_status.replace('_', ' ')}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => void handleAddApplication()}
                  disabled={addingApplication}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/15 px-4 py-2.5 text-sm font-medium text-white/55 transition-colors hover:bg-white/[0.04] disabled:opacity-50 sm:w-auto"
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
          </div>
        )}
      </div>
    </div>
  )
}
