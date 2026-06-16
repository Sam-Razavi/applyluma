import { useCallback, useEffect, useRef, useState } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import JobCard from '../components/discover/JobCard'
import { DEFAULT_FILTERS } from '../components/discover/defaultFilters'
import JobFilters from '../components/discover/JobFilters'
import JobDetail from '../components/discover/JobDetail'
import { FadeIn } from '../components/ui/FadeIn'
import { SkeletonCard } from '../components/ui/SkeletonCard'
import { staggerItem } from '../lib/animations'
import { deleteSavedJob, fetchDiscoveredJobs, saveJob } from '../services/jobDiscoveryApi'
import type { DiscoveredJob, JobFilters as Filters } from '../types/jobDiscovery'

const PAGE_SIZE = 20

export default function Discover() {
  const [jobs, setJobs] = useState<DiscoveredJob[]>([])
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [initialLoad, setInitialLoad] = useState(true)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [searchInput, setSearchInput] = useState('')
  const savedJobMapRef = useRef<Map<string, string>>(new Map())
  const abortRef = useRef<AbortController | null>(null)
  const filtersRef = useRef<Filters>(filters)
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Keep a ref to the latest filters so the debounced search reads fresh values.
  filtersRef.current = filters

  useEffect(() => {
    document.title = 'Discover Jobs | ApplyLuma'
  }, [])

  // Clear any pending debounce on unmount.
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    }
  }, [])

  const loadJobs = useCallback(
    async (nextFilters: Filters, nextPage: number, replace: boolean) => {
      abortRef.current?.abort()
      abortRef.current = new AbortController()

      setLoading(true)
      try {
        const results = await fetchDiscoveredJobs({
          ...nextFilters,
          page: nextPage,
          limit: PAGE_SIZE,
        })
        setJobs((prev) => (replace ? results : [...prev, ...results]))
        setHasMore(results.length === PAGE_SIZE)
        // Track which jobs are saved and their saved_job_id for unsaving
        setSavedIds((prev) => {
          const next = new Set(prev)
          results.forEach((j) => {
            if (j.is_saved) {
              next.add(j.job_id)
              if (j.saved_job_id) savedJobMapRef.current.set(j.job_id, j.saved_job_id)
            } else {
              next.delete(j.job_id)
            }
          })
          return next
        })
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return
        toast.error('Failed to load jobs')
      } finally {
        setLoading(false)
        setInitialLoad(false)
      }
    },
    [],
  )

  // Initial load
  useEffect(() => {
    void loadJobs(filters, 1, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function applyFilters(next: Filters) {
    setFilters(next)
    setPage(1)
    void loadJobs(next, 1, true)
  }

  function resetFilters() {
    setSearchInput('')
    applyFilters(DEFAULT_FILTERS)
  }

  function handleSearchChange(value: string) {
    setSearchInput(value)
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    searchDebounceRef.current = setTimeout(() => {
      applyFilters({ ...filtersRef.current, search: value })
    }, 350)
  }

  function loadMore() {
    const next = page + 1
    setPage(next)
    void loadJobs(filters, next, false)
  }

  async function handleSave(job: DiscoveredJob) {
    if (savedIds.has(job.job_id)) {
      const savedJobId = savedJobMapRef.current.get(job.job_id)
      if (!savedJobId) return
      setSavedIds((prev) => { const next = new Set(prev); next.delete(job.job_id); return next })
      setJobs((prev) => prev.map((j) => (j.job_id === job.job_id ? { ...j, is_saved: false } : j)))
      try {
        await deleteSavedJob(savedJobId)
        savedJobMapRef.current.delete(job.job_id)
        toast('Job unsaved')
      } catch {
        setSavedIds((prev) => new Set(prev).add(job.job_id))
        setJobs((prev) => prev.map((j) => (j.job_id === job.job_id ? { ...j, is_saved: true } : j)))
        toast.error('Failed to unsave job')
      }
      return
    }
    setSavedIds((prev) => new Set(prev).add(job.job_id))
    setJobs((prev) => prev.map((j) => (j.job_id === job.job_id ? { ...j, is_saved: true } : j)))
    toast.success('Job saved!')
    try {
      const result = await saveJob({ job_id: job.job_id })
      savedJobMapRef.current.set(job.job_id, result.id)
    } catch {
      setSavedIds((prev) => { const next = new Set(prev); next.delete(job.job_id); return next })
      setJobs((prev) => prev.map((j) => (j.job_id === job.job_id ? { ...j, is_saved: false } : j)))
      toast.error('Failed to save job')
    }
  }

  const selectedJobSaved = selectedJobId ? savedIds.has(selectedJobId) : false

  return (
    <FadeIn>
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Discover Jobs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Search and explore job listings matched to your CV.
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <MagnifyingGlassIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search jobs by title or company"
          aria-label="Search jobs by title or company"
          className="w-full rounded-2xl border border-gray-200 bg-white py-3 pl-12 pr-4 text-sm placeholder-gray-400 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        {/* Filters sidebar */}
        <JobFilters filters={filters} onChange={applyFilters} onReset={resetFilters} />

        {/* Job list */}
        <div className="w-full space-y-4 lg:flex-1 lg:min-w-0">
          {initialLoad ? (
            <div className="grid gap-4">
              {[...Array(6)].map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gray-50">
                <MagnifyingGlassIcon className="h-6 w-6 text-gray-400" />
              </div>
              <h2 className="mt-4 text-sm font-semibold text-gray-900">No jobs found</h2>
              <p className="mt-1 text-sm text-gray-400">
                Try adjusting your filters or check back after the next scraping run.
              </p>
            </div>
          ) : (
            <>
              <div className="grid gap-4">
                {jobs.map((job, index) => (
                  <motion.div
                    key={job.job_id}
                    className="w-full min-w-0"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={staggerItem(index % PAGE_SIZE)}
                  >
                    <JobCard
                      job={{ ...job, is_saved: savedIds.has(job.job_id) }}
                      onClick={(j) => setSelectedJobId(j.job_id)}
                      onSave={handleSave}
                    />
                  </motion.div>
                ))}
              </div>

              {hasMore && (
                <div className="flex justify-center pt-2">
                  <button
                    type="button"
                    onClick={loadMore}
                    disabled={loading}
                    className="rounded-xl border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    {loading ? 'Loading…' : 'Load more'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Detail modal */}
      <JobDetail
        jobId={selectedJobId}
        isSaved={selectedJobSaved}
        onClose={() => setSelectedJobId(null)}
        onSave={(id) => {
          const job = jobs.find((j) => j.job_id === id)
          if (job) void handleSave(job)
        }}
        onApplicationCreated={(id, applicationId, status) => {
          setJobs((prev) =>
            prev.map((job) =>
              job.job_id === id
                ? { ...job, application_id: applicationId, application_status: status }
                : job,
            ),
          )
        }}
      />
    </div>
    </FadeIn>
  )
}
