import { useEffect, useState } from 'react'
import {
  ArrowTopRightOnSquareIcon,
  BookmarkIcon as BookmarkOutline,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { BookmarkIcon as BookmarkSolid } from '@heroicons/react/24/solid'
import type { DiscoveredJobDetail } from '../../types/jobDiscovery'
import { SOURCE_LABELS } from '../../types/jobDiscovery'
import { fetchJobDetail } from '../../services/jobDiscoveryApi'

interface Props {
  jobId: string | null
  isSaved: boolean
  onClose: () => void
  onSave: (jobId: string) => void
}

function Pill({ text, color }: { text: string; color: string }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{text}</span>
  )
}

export default function JobDetail({ jobId, isSaved, onClose, onSave }: Props) {
  const [job, setJob] = useState<DiscoveredJobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
                  <span className="text-lg font-bold text-primary-700">
                    {Math.round(job.match_score)}%
                  </span>
                </div>
                {job.explanation && (
                  <p className="text-xs text-primary-700">{job.explanation}</p>
                )}
              </div>
            )}

            {/* Matched / missing skills */}
            {(job.matched_skills.length > 0 || job.missing_skills.length > 0) && (
              <div className="grid grid-cols-2 gap-4">
                {job.matched_skills.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-green-700">Matched skills</p>
                    <div className="flex flex-wrap gap-1">
                      {job.matched_skills.map((s) => (
                        <Pill key={s} text={s} color="bg-green-50 text-green-700" />
                      ))}
                    </div>
                  </div>
                )}
                {job.missing_skills.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-red-700">Missing skills</p>
                    <div className="flex flex-wrap gap-1">
                      {job.missing_skills.map((s) => (
                        <Pill key={s} text={s} color="bg-red-50 text-red-700" />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

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
