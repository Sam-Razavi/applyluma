import { ArrowPathIcon } from '@heroicons/react/24/outline'

interface AnalyticsHeaderProps {
  onRefresh: () => void
  refreshing: boolean
  lastRefresh?: Date | null
}

export default function AnalyticsHeader({
  onRefresh,
  refreshing,
  lastRefresh,
}: AnalyticsHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Market Intelligence</h1>
        <p className="mt-2 text-sm text-gray-500">Real-time job market insights and analytics</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 rounded-lg bg-primary-50 px-3 py-2 sm:flex">
          <div className="h-2 w-2 animate-pulse rounded-full bg-primary-600" />
          <span className="text-xs font-medium text-primary-700">
            {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : 'Updated daily'}
          </span>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all duration-200 ease-in-out hover:bg-gray-50 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ArrowPathIcon className={`h-4 w-4 transition-transform ${refreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>
    </div>
  )
}
