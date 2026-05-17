import { ExclamationCircleIcon } from '@heroicons/react/24/outline'

interface Props {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Something went wrong', onRetry }: Props) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-red-50">
        <ExclamationCircleIcon className="h-6 w-6 text-red-400" />
      </div>
      <h2 className="mt-4 text-sm font-semibold text-gray-900">{message}</h2>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-block rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          Try again
        </button>
      )}
    </div>
  )
}
