import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface ErrorBannerProps {
  message: string
  className?: string
}

export default function ErrorBanner({ message, className = '' }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={`flex items-center gap-2 rounded-xl border border-chip-danger bg-chip-danger px-4 py-3 text-sm text-chip-danger-fg ${className}`}
    >
      <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
      {message}
    </div>
  )
}
