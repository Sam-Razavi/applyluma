import { ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface ErrorStateProps {
  error: string
  onRetry?: () => void
}

export default function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="flex h-64 flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 rounded-full bg-danger-50 p-4">
        <ExclamationCircleIcon className="h-8 w-8 text-danger-500" aria-hidden="true" />
      </div>

      <h3 className="text-sm font-semibold text-gray-700">Failed to load data</h3>
      <p className="mt-1 max-w-sm text-xs text-gray-500">{error}</p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm font-medium text-primary-600 transition-colors duration-200 hover:text-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          Try again
        </button>
      )}
    </div>
  )
}
