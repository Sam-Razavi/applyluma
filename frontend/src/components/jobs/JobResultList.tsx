import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import JobResultCard from './JobResultCard'
import type { ApplicationCreate } from '../../types/application'
import type { JobSearchResponse } from '../../services/jobSearchApi'

interface Props {
  data: JobSearchResponse
  onPageChange: (page: number) => void
  onTrack: (data: Partial<ApplicationCreate>) => void
}

export default function JobResultList({ data, onPageChange, onTrack }: Props) {
  const hasPrevious = data.page > 1
  const hasNext = data.total_pages === 0 ? false : data.page < data.total_pages

  return (
    <div className="space-y-4">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <p className="text-sm text-gray-500">
          {data.count === 0 ? 'No jobs found' : `${data.count.toLocaleString()} jobs found`}
        </p>
        {data.total_pages > 0 && (
          <p className="text-sm text-gray-400">
            Page {data.page} of {data.total_pages}
          </p>
        )}
      </div>

      <div className="grid gap-4">
        {data.results.map((job) => (
          <JobResultCard key={job.id} job={job} onTrack={onTrack} />
        ))}
      </div>

      {(hasPrevious || hasNext) && (
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onPageChange(data.page - 1)}
            disabled={!hasPrevious}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-sm font-medium text-gray-700 ring-1 ring-gray-200 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeftIcon className="h-4 w-4" />
            Previous
          </button>
          <button
            type="button"
            onClick={() => onPageChange(data.page + 1)}
            disabled={!hasNext}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-sm font-medium text-gray-700 ring-1 ring-gray-200 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
