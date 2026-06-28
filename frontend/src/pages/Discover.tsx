import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ExclamationTriangleIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import JobCard from '../components/discover/JobCard'
import { DEFAULT_FILTERS } from '../components/discover/defaultFilters'
import JobFilters from '../components/discover/JobFilters'
import JobDetail from '../components/discover/JobDetail'
import AddApplicationModal from '../components/applications/AddApplicationModal'
import JobSearchBar, { type SearchSource } from '../components/jobs/JobSearchBar'
import JobResultList from '../components/jobs/JobResultList'
import SearchJobDetail from '../components/jobs/SearchJobDetail'
import { FadeIn } from '../components/ui/FadeIn'
import { SkeletonCard } from '../components/ui/SkeletonCard'
import { staggerItem } from '../lib/animations'
import { deleteSavedJob, fetchDiscoveredJobs, saveJob } from '../services/jobDiscoveryApi'
import { searchJobs, type AdzunaJobResult, type JobSearchResponse } from '../services/jobSearchApi'
import type { ApplicationCreate } from '../types/application'
import type { DiscoveredJob, JobFilters as Filters } from '../types/jobDiscovery'

const PAGE_SIZE = 20

type Tab = 'for-you' | 'search'

const RECENT_KEY = 'recent_job_searches'
const LOCATION_KEY = 'preferred_job_location'
const MAX_RECENT = 5

interface RecentSearch {
  query: string
  location: string
}

function loadRecentSearches(): RecentSearch[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]') as RecentSearch[]
  } catch {
    return []
  }
}

function saveRecentSearch(query: string, location: string) {
  const existing = loadRecentSearches().filter(
    (r) => !(r.query === query && r.location === location),
  )
  const updated = [{ query, location }, ...existing].slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
}

const emptyResults: JobSearchResponse = {
  results: [],
  count: 0,
  page: 1,
  total_pages: 0,
}

export default function Discover() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as Tab) === 'search' ? 'search' : 'for-you'
  const [tab, setTab] = useState<Tab>(initialTab)

  function switchTab(t: Tab) {
    setTab(t)
    setSearchParams(t === 'for-you' ? {} : { tab: t }, { replace: true })
  }

  // ── For You state ─────────────────────────────────────────────────────
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

  filtersRef.current = filters

  // ── Search tab state ──────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLocation, setSearchLocation] = useState(() => localStorage.getItem(LOCATION_KEY) ?? '')
  const [searchSource, setSearchSource] = useState<SearchSource>('all')
  const [searchData, setSearchData] = useState<JobSearchResponse>(emptyResults)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [trackData, setTrackData] = useState<Partial<ApplicationCreate> | null>(null)
  const [trackOpen, setTrackOpen] = useState(false)
  const [selectedSearchJob, setSelectedSearchJob] = useState<AdzunaJobResult | null>(null)
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>(loadRecentSearches)

  useEffect(() => {
    document.title = tab === 'search' ? 'Search Jobs | ApplyLuma' : 'Discover Jobs | ApplyLuma'
  }, [tab])

  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    }
  }, [])

  // ── For You: load jobs ────────────────────────────────────────────────
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

  // ── Search tab: run search ────────────────────────────────────────────
  async function runSearch(nextQuery: string, nextLocation: string, nextPage = 1) {
    if (!nextQuery.trim()) {
      toast.error('Enter a role, skill, or keyword')
      return
    }

    setSearchLoading(true)
    setSearchError(null)
    setHasSearched(true)
    setSearchQuery(nextQuery)
    setSearchLocation(nextLocation)
    localStorage.setItem(LOCATION_KEY, nextLocation)

    if (nextPage === 1) {
      saveRecentSearch(nextQuery, nextLocation)
      setRecentSearches(loadRecentSearches())
    }

    try {
      setSearchData(await searchJobs(nextQuery, nextLocation, nextPage, 10, searchSource))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to search jobs'
      setSearchError(message)
      setSearchData(emptyResults)
    } finally {
      setSearchLoading(false)
    }
  }

  function removeRecentSearch(index: number) {
    const updated = recentSearches.filter((_, i) => i !== index)
    localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
    setRecentSearches(updated)
  }

  function handleTrack(data: Partial<ApplicationCreate>) {
    setTrackData(data)
    setTrackOpen(true)
  }

  function closeTrackModal() {
    setTrackOpen(false)
    setTrackData(null)
  }

  return (
    <FadeIn>
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-fg">Discover Jobs</h1>
        <p className="mt-1 text-sm text-fg-subtle">
          {tab === 'search'
            ? 'Search live job listings from Adzuna and Platsbanken.'
            : 'Explore job listings matched to your CV.'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-surface p-1 w-fit">
        {([
          { key: 'for-you' as Tab, label: 'For You' },
          { key: 'search' as Tab, label: 'Search' },
        ]).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => switchTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab === key
                ? 'bg-surface text-fg shadow-sm'
                : 'text-fg-subtle hover:text-fg-muted'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── For You tab ──────────────────────────────────────────────────── */}
      {tab === 'for-you' && (
        <>
          {/* Search bar */}
          <div className="relative">
            <MagnifyingGlassIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-fg-subtle" />
            <input
              type="search"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search jobs by title or company"
              aria-label="Search jobs by title or company"
              className="w-full rounded-2xl border border-line bg-surface py-3 pl-12 pr-4 text-sm placeholder-fg-subtle shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
            <JobFilters filters={filters} onChange={applyFilters} onReset={resetFilters} />

            <div className="w-full space-y-4 lg:flex-1 lg:min-w-0">
              {initialLoad ? (
                <div className="grid gap-4">
                  {[...Array(6)].map((_, i) => (
                    <SkeletonCard key={i} />
                  ))}
                </div>
              ) : jobs.length === 0 ? (
                <div className="rounded-2xl border border-line bg-surface px-6 py-16 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-surface">
                    <MagnifyingGlassIcon className="h-6 w-6 text-fg-subtle" />
                  </div>
                  <h2 className="mt-4 text-sm font-semibold text-fg">No jobs found</h2>
                  <p className="mt-1 text-sm text-fg-subtle">
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
                        className="rounded-xl border border-line-strong px-6 py-2.5 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50"
                      >
                        {loading ? 'Loading…' : 'Load more'}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

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
        </>
      )}

      {/* ── Search tab ───────────────────────────────────────────────────── */}
      {tab === 'search' && (
        <div className="space-y-6">
          <JobSearchBar
            loading={searchLoading}
            initialLocation={searchLocation}
            source={searchSource}
            onSourceChange={setSearchSource}
            onSearch={(q, loc) => void runSearch(q, loc)}
          />

          {recentSearches.length > 0 && !hasSearched && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-fg-subtle">Recent:</span>
              {recentSearches.map((r, i) => (
                <span
                  key={i}
                  className="group flex items-center gap-1 rounded-full border border-line bg-surface pl-3 pr-1.5 py-1 text-xs text-fg-muted hover:border-primary-300 hover:text-accent-text cursor-pointer transition-colors"
                >
                  <button
                    type="button"
                    className="focus:outline-none"
                    onClick={() => void runSearch(r.query, r.location)}
                  >
                    {r.query}{r.location ? ` · ${r.location}` : ''}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); removeRecentSearch(i) }}
                    className="ml-0.5 rounded-full p-0.5 text-fg-subtle hover:bg-surface-strong hover:text-fg-muted focus:outline-none"
                    aria-label="Remove recent search"
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {searchError && (
            <div className="flex items-center gap-2 rounded-xl border border-chip-danger bg-chip-danger px-4 py-3 text-sm text-chip-danger-fg">
              <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
              {searchError}
            </div>
          )}

          {searchLoading ? (
            <div className="grid gap-4">
              {[...Array(4)].map((_, index) => (
                <div key={index} className="h-44 animate-pulse rounded-2xl bg-track" />
              ))}
            </div>
          ) : hasSearched && searchData.results.length > 0 ? (
            <JobResultList
              data={searchData}
              onTrack={handleTrack}
              onJobClick={setSelectedSearchJob}
              onPageChange={(p) => void runSearch(searchQuery, searchLocation, p)}
            />
          ) : (
            <div className="rounded-2xl border border-line bg-surface px-6 py-16 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary-900/20">
                <MagnifyingGlassIcon className="h-6 w-6 text-accent-text" />
              </div>
              <h2 className="mt-4 text-sm font-semibold text-fg">
                {hasSearched ? 'No jobs found' : 'Search live job listings'}
              </h2>
              <p className="mt-1 text-sm text-fg-subtle">
                {hasSearched
                  ? 'Try a broader keyword or a different location.'
                  : 'Search Adzuna and Platsbanken for roles, skills, or companies.'}
              </p>
            </div>
          )}

          <SearchJobDetail
            job={selectedSearchJob}
            onClose={() => setSelectedSearchJob(null)}
            onTrack={handleTrack}
          />

          <AddApplicationModal
            open={trackOpen}
            onClose={closeTrackModal}
            initialData={trackData}
          />
        </div>
      )}
    </div>
    </FadeIn>
  )
}
