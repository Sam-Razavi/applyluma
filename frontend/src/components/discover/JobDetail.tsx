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
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4 bg-black/40"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
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
          <div className="p-8 text-center text-sm text-red-600">{error}</div>
        )}

        {job && !loading && (
          <div className="p-6 space-y-5">
            {/* Header */}
            <div className="pr-8 space-y-1">
              <h2 className="text-xl font-bold text-gray-900">{job.title}</h2>
              <p className="text-sm text-gray-600">{job.company}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                {job.location && (
                  <Pill text={job.location} color="bg-gray-100 text-gray-600" />
                )}
                {job.remote_allowed && (
                  <Pill text="Remote" color="bg-blue-50 text-blue-700" />
                )}
                {job.employment_type && (
                  <Pill
                    text={job.employment_type.replace('_', ' ')}
                    color="bg-gray-100 text-gray-600"
                  />
                )}
                <Pill
                  text={SOURCE_LABELS[job.source] ?? job.source}
                  color="bg-gray-100 text-gray-500"
                />
              </div>
            </div>

            {/* Match score summary */}
            {job.match_score !== null && (
              <div className="rounded-xl border border-primary-100 bg-primary-50 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-primary-800">Match score</span>
                  <span
                    className="text-lg font-bold text-primary-700"
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
                <h3 className="mb-2 text-sm font-semibold text-gray-900">Job description</h3>
                <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-line text-sm leading-relaxed">
                  {job.description}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 border-t border-gray-100 pt-4">
              <button
                type="button"
                onClick={() => onSave(job.job_id)}
                className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
                  isSaved
                    ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
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
                className="flex items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-100"
              >
                <SparklesIcon className="h-4 w-4" />
                Tailor CV
              </button>
              {job.application_status ? (
                <span className="flex items-center gap-2 rounded-xl bg-green-50 px-4 py-2.5 text-sm font-medium text-green-700">
                  <BriefcaseIcon className="h-4 w-4" />
                  {job.application_status.replace('_', ' ')}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => void handleAddApplication()}
                  disabled={addingApplication}
                  className="flex items-center gap-2 rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                >
                  <BriefcaseIcon className="h-4 w-4" />
                  {addingApplication ? 'Adding' : 'Add to Applications'}
                </button>
              )}
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700"
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
