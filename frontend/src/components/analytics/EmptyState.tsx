import { ChartBarIcon } from '@heroicons/react/24/outline'

interface EmptyStateProps {
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({
  title = 'No data available',
  description = 'Data will appear here once the analytics pipeline runs',
  action,
}: EmptyStateProps) {
  return (
    <div className="flex h-48 flex-col items-center justify-center px-6 text-center md:h-72">
      <div className="mb-4 rounded-full bg-gray-100 p-4">
        <ChartBarIcon className="h-8 w-8 text-gray-400" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      <p className="mt-1 max-w-sm text-xs text-gray-500">{description}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-200 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
