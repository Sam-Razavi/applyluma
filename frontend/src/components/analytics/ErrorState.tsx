import { ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface ErrorStateProps {
  error: string
  onRetry?: () => void
}

export default function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="flex h-48 flex-col items-center justify-center px-6 text-center md:h-72">
      <div className="mb-4 rounded-full bg-chip-danger p-4">
        <ExclamationCircleIcon className="h-8 w-8 text-danger-500" aria-hidden="true" />
      </div>

      <h3 className="text-sm font-semibold text-fg-muted">Failed to load data</h3>
      <p className="mt-1 max-w-sm text-xs text-fg-subtle">{error}</p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm font-medium text-accent-text transition-colors duration-200 hover:text-accent-text focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          Try again
        </button>
      )}
    </div>
  )
}
