import type { ComponentType, SVGProps } from 'react'
import { ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { FadeIn } from './FadeIn'

interface ErrorStateProps {
  title?: string
  description: string
  onRetry?: () => void
  retryLabel?: string
  icon?: ComponentType<SVGProps<SVGSVGElement>>
  size?: 'compact' | 'default' | 'full'
  className?: string
}

const SIZE_CLASSES: Record<NonNullable<ErrorStateProps['size']>, string> = {
  compact: 'px-4 py-6',
  default: 'h-48 px-6 md:h-72',
  full: 'min-h-[50vh] px-6 py-16',
}

const ICON_WRAPPER_CLASSES: Record<NonNullable<ErrorStateProps['size']>, string> = {
  compact: 'mb-3 p-3',
  default: 'mb-4 p-4',
  full: 'mb-5 p-5',
}

const ICON_CLASSES: Record<NonNullable<ErrorStateProps['size']>, string> = {
  compact: 'h-5 w-5',
  default: 'h-8 w-8',
  full: 'h-10 w-10',
}

const TITLE_CLASSES: Record<NonNullable<ErrorStateProps['size']>, string> = {
  compact: 'text-xs font-semibold text-fg-muted',
  default: 'text-sm font-semibold text-fg-muted',
  full: 'text-lg font-semibold text-fg',
}

const DESCRIPTION_CLASSES: Record<NonNullable<ErrorStateProps['size']>, string> = {
  compact: 'mt-1 max-w-sm text-xs text-fg-subtle',
  default: 'mt-1 max-w-sm text-xs text-fg-subtle',
  full: 'mt-2 max-w-md text-sm text-fg-subtle',
}

function ErrorStateContent({
  title = 'Something went wrong',
  description,
  onRetry,
  retryLabel = 'Try again',
  icon: Icon = ExclamationCircleIcon,
  size = 'default',
  className = '',
}: ErrorStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${SIZE_CLASSES[size]} ${className}`}
    >
      <div className={`rounded-full bg-chip-danger ${ICON_WRAPPER_CLASSES[size]}`}>
        <Icon className={`${ICON_CLASSES[size]} text-chip-danger-fg`} aria-hidden="true" />
      </div>

      <h3 className={TITLE_CLASSES[size]}>{title}</h3>
      <p className={DESCRIPTION_CLASSES[size]}>{description}</p>

      {onRetry &&
        (size === 'full' ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-200 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {retryLabel}
          </button>
        ) : (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 text-sm font-medium text-accent-text transition-colors duration-200 hover:text-accent-text focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {retryLabel}
          </button>
        ))}
    </div>
  )
}

export default function ErrorState(props: ErrorStateProps) {
  if (props.size === 'full') {
    return (
      <FadeIn>
        <ErrorStateContent {...props} />
      </FadeIn>
    )
  }
  return <ErrorStateContent {...props} />
}
