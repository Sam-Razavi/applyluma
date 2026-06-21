import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookmarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import SavedJobCard from '../components/discover/SavedJobCard'
import JobDetail from '../components/discover/JobDetail'
import { fetchSavedJobs, updateSavedJob, deleteSavedJob } from '../services/jobDiscoveryApi'
import { createApplication } from '../services/applicationsApi'
import type { SavedJob } from '../types/jobDiscovery'

export default function SavedJobs() {
  const [saved, setSaved] = useState<SavedJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'alpha'>('date')
  const [addingAppFor, setAddingAppFor] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Saved Jobs | ApplyLuma'
    fetchSavedJobs()
      .then(setSaved)
      .catch(() => toast.error('Failed to load saved jobs'))
      .finally(() => setLoading(false))
  }, [])

  const displayed = useMemo(() => {
    let result = saved

    const q = search.trim().toLowerCase()
    if (q) {
      result = result.filter((s) =>
        [s.job?.title ?? '', s.job?.company ?? ''].some((v) =>
          v.toLowerCase().includes(q),
        ),
      )
    }

    return [...result].sort((a, b) => {
      if (a.starred !== b.starred) return a.starred ? -1 : 1
      if (sortBy === 'alpha') {
        return (a.job?.title ?? '').toLowerCase().localeCompare((b.job?.title ?? '').toLowerCase())
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  }, [saved, search, sortBy])

  async function handleStar(savedId: string, starred: boolean) {
    setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred } : s)))
    try {
      const updated = await updateSavedJob(savedId, { starred })
      setSaved((prev) => prev.map((s) => (s.id === savedId ? updated : s)))
    } catch {
      setSaved((prev) => prev.map((s) => (s.id === savedId ? { ...s, starred: !starred } : s)))
      toast.error('Failed to update')
    }
  }

  async function handleDelete(savedId: string) {
    const removed = saved.find((s) => s.id === savedId)
    setSaved((prev) => prev.filter((s) => s.id !== savedId))
    toast.success('Removed from saved jobs')
    try {
      await deleteSavedJob(savedId)
    } catch {
      if (removed) setSaved((prev) => [...prev, removed])
      toast.error('Failed to remove')
    }
  }

  async function handleAddToApplications(item: SavedJob) {
    setAddingAppFor(item.id)
    try {
      const application = await createApplication({
        raw_job_posting_id: item.raw_job_posting_id,
        status: 'wishlist',
      })
      setSaved((prev) =>
        prev.map((s) =>
          s.id === item.id && s.job
            ? {
                ...s,
                job: {
                  ...s.job,
                  application_id: application.id,
                  application_status: application.status,
                },
              }
            : s,
        ),
      )
      toast.success('Added to applications')
    } catch {
      toast.error('Failed to add application')
    } finally {
      setAddingAppFor(null)
    }
  }

  function handleApplicationCreated(jobId: string, applicationId: string, status: string) {
    setSaved((prev) =>
      prev.map((s) =>
        s.raw_job_posting_id === jobId && s.job
          ? {
              ...s,
              job: {
                ...s.job,
                application_id: applicationId,
                application_status: status,
              },
            }
          : s,
      ),
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white/90">Saved Jobs</h1>
        <p className="mt-1 text-sm text-white/30">
          {search.trim()
            ? `${displayed.length} of ${saved.length} saved ${saved.length === 1 ? 'job' : 'jobs'}`
            : `${saved.length} saved ${saved.length === 1 ? 'job' : 'jobs'}`}
        </p>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-2xl bg-white/[0.04]" />
          ))}
        </div>
      ) : saved.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-16 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.03]">
            <BookmarkIcon className="h-6 w-6 text-white/30" />
          </div>
          <h2 className="mt-4 text-sm font-semibold text-white/90">No saved jobs yet</h2>
          <p className="mt-1 text-sm text-white/30">
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
          {/* Search + sort toolbar */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by title or company..."
                className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-2.5 pl-9 pr-4 text-sm text-white/90 placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'date' | 'alpha')}
              className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white/90 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="date">Newest saved</option>
              <option value="alpha">A–Z by title</option>
            </select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {displayed.map((s) => (
              <SavedJobCard
                key={s.id}
                saved={s}
                onClick={setSelectedJobId}
                onStar={handleStar}
                onDelete={handleDelete}
                onAddToApplications={handleAddToApplications}
                addingToApplications={addingAppFor === s.id}
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
        onApplicationCreated={handleApplicationCreated}
      />
    </div>
  )
}
