import { type ReactNode } from 'react'
import EmptyState from './EmptyState'
import ErrorState from './ErrorState'
import LoadingSkeleton from './LoadingSkeleton'

interface ChartCardProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  loading?: boolean
  error?: string | null
  empty?: boolean
  emptyMessage?: string
  actions?: ReactNode
  onRetry?: () => void
}

export default function ChartCard({
  title,
  subtitle,
  children,
  className = '',
  loading = false,
  error = null,
  empty = false,
  emptyMessage,
  actions,
  onRetry,
}: ChartCardProps) {
  return (
    <section
      role="region"
      aria-label={`${title} chart`}
      tabIndex={0}
      className={`rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow duration-200 ease-in-out hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${className}`}
    >
      <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-gray-900">{title}</h2>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>

      <div className="p-6">
        {loading ? (
          <LoadingSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : empty ? (
          <EmptyState description={emptyMessage} />
        ) : (
          children
        )}
      </div>
    </section>
  )
}
