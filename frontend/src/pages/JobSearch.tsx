import { useEffect, useState } from 'react'
import { ExclamationTriangleIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import AddApplicationModal from '../components/applications/AddApplicationModal'
import JobResultList from '../components/jobs/JobResultList'
import JobSearchBar from '../components/jobs/JobSearchBar'
import { searchJobs, type JobSearchResponse } from '../services/jobSearchApi'
import type { ApplicationCreate } from '../types/application'

const emptyResults: JobSearchResponse = {
  results: [],
  count: 0,
  page: 1,
  total_pages: 0,
}

export default function JobSearch() {
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [data, setData] = useState<JobSearchResponse>(emptyResults)
  const [hasSearched, setHasSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [trackData, setTrackData] = useState<Partial<ApplicationCreate> | null>(null)
  const [trackOpen, setTrackOpen] = useState(false)

  useEffect(() => {
    document.title = 'Job Search | ApplyLuma'
  }, [])

  async function runSearch(nextQuery: string, nextLocation: string, nextPage = 1) {
    if (!nextQuery.trim()) {
      toast.error('Enter a role, skill, or keyword')
      return
    }

    setLoading(true)
    setError(null)
    setHasSearched(true)
    setQuery(nextQuery)
    setLocation(nextLocation)

    try {
      setData(await searchJobs(nextQuery, nextLocation, nextPage))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to search jobs'
      setError(message)
      setData(emptyResults)
    } finally {
      setLoading(false)
    }
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Job Search</h1>
        <p className="mt-1 text-sm text-gray-500">
          Search live job listings and add promising roles to your application tracker.
        </p>
      </div>

      <JobSearchBar loading={loading} onSearch={(q, loc) => void runSearch(q, loc)} />

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4">
          {[...Array(4)].map((_, index) => (
            <div key={index} className="h-44 animate-pulse rounded-2xl bg-gray-100" />
          ))}
        </div>
      ) : hasSearched && data.results.length > 0 ? (
        <JobResultList
          data={data}
          onTrack={handleTrack}
          onPageChange={(page) => void runSearch(query, location, page)}
        />
      ) : (
        <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50">
            <MagnifyingGlassIcon className="h-6 w-6 text-brand-500" />
          </div>
          <h2 className="mt-4 text-sm font-semibold text-gray-900">
            {hasSearched ? 'No jobs found' : 'Search for live job listings'}
          </h2>
          <p className="mt-1 text-sm text-gray-400">
            {hasSearched
              ? 'Try a broader keyword or a different location.'
              : 'Start with a role, skill, or company keyword.'}
          </p>
        </div>
      )}

      <AddApplicationModal
        open={trackOpen}
        onClose={closeTrackModal}
        initialData={trackData}
      />
    </div>
  )
}
