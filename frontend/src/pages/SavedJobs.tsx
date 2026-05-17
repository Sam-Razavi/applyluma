import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookmarkIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import SavedJobCard from '../components/discover/SavedJobCard'
import JobDetail from '../components/discover/JobDetail'
import { fetchSavedJobs, updateSavedJob, deleteSavedJob } from '../services/jobDiscoveryApi'
import type { SavedJob } from '../types/jobDiscovery'
import { ErrorState } from '../components/ui/ErrorState'
import { extractApiError } from '../utils/errors'

export default function SavedJobs() {
  const [saved, setSaved] = useState<SavedJob[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [activeCollection, setActiveCollection] = useState<string | null>(null)

  function doFetch() {
    setLoading(true)
    setLoadError(false)
    fetchSavedJobs()
      .then(setSaved)
      .catch((err) => {
        setLoadError(true)
        toast.error(extractApiError(err, 'Failed to load saved jobs'))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    document.title = 'Saved Jobs | ApplyLuma'
    doFetch()
  }, [])

  async function handleStar(savedId: string, starred: boolean) {
    setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred } : s)))
    try {
      const updated = await updateSavedJob(savedId, { starred })
      setSaved((prev) => prev.map((s) => (s.id === savedId ? updated : s)))
    } catch (err) {
      setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred: !starred } : s)))
      toast.error(extractApiError(err, 'Failed to update'))
    }
  }

  async function handleDelete(savedId: string) {
    const removed = saved.find((s) => s.id === savedId)
    setSaved((prev) => prev.filter((s) => s.id !== savedId))
    toast.success('Removed from saved jobs')
    try {
      await deleteSavedJob(savedId)
    } catch (err) {
      if (removed) setSaved((prev) => [...prev, removed])
      toast.error(extractApiError(err, 'Failed to remove'))
    }
  }

  const collections = [...new Set(saved.map((s) => s.list_name ?? 'Saved'))]
  const displayed =
    activeCollection === null
      ? saved
      : saved.filter((s) => (s.list_name ?? 'Saved') === activeCollection)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Saved Jobs</h1>
        <p className="mt-1 text-sm text-gray-500">
          {saved.length} saved {saved.length === 1 ? 'job' : 'jobs'}
        </p>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-2xl bg-gray-100" />
          ))}
        </div>
      ) : loadError ? (
        <ErrorState message="Failed to load saved jobs" onRetry={doFetch} />
      ) : saved.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gray-50">
            <BookmarkIcon className="h-6 w-6 text-gray-400" />
          </div>
          <h2 className="mt-4 text-sm font-semibold text-gray-900">No saved jobs yet</h2>
          <p className="mt-1 text-sm text-gray-400">
            Browse the Discover page and save jobs you're interested in.
          </p>
          <Link
            to="/discover"
            className="mt-4 inline-block rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            Discover Jobs
          </Link>
        </div>
      ) : (
        <>
          {/* Collection tabs */}
          {collections.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              <button
                type="button"
                onClick={() => setActiveCollection(null)}
                className={`rounded-full px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeCollection === null
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                All ({saved.length})
              </button>
              {collections.map((col) => (
                <button
                  key={col}
                  type="button"
                  onClick={() => setActiveCollection(col)}
                  className={`rounded-full px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors ${
                    activeCollection === col
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {col} ({saved.filter((s) => (s.list_name ?? 'Saved') === col).length})
                </button>
              ))}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            {displayed.map((s) => (
              <SavedJobCard
                key={s.id}
                saved={s}
                onClick={setSelectedJobId}
                onStar={handleStar}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </>
      )}

      {/* Job detail modal */}
      <JobDetail
        jobId={selectedJobId}
        isSaved={true}
        onClose={() => setSelectedJobId(null)}
        onSave={() => {}}
      />
    </div>
  )
}
