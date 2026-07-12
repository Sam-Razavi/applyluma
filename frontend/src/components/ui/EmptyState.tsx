import type { ComponentType, SVGProps } from 'react'
import { InboxIcon } from '@heroicons/react/24/outline'
import { FadeIn } from './FadeIn'

interface EmptyStateAction {
  label: string
  onClick: () => void
}

interface EmptyStateProps {
  title?: string
  description?: string
  action?: EmptyStateAction
  icon?: ComponentType<SVGProps<SVGSVGElement>>
  size?: 'compact' | 'default' | 'full'
  className?: string
}

const SIZE_CLASSES: Record<NonNullable<EmptyStateProps['size']>, string> = {
  compact: 'px-4 py-6',
  default: 'h-48 px-6 md:h-72',
  full: 'min-h-[50vh] px-6 py-16',
}

const ICON_WRAPPER_CLASSES: Record<NonNullable<EmptyStateProps['size']>, string> = {
  compact: 'mb-3 p-3',
  default: 'mb-4 p-4',
  full: 'mb-5 p-5',
}

const ICON_CLASSES: Record<NonNullable<EmptyStateProps['size']>, string> = {
  compact: 'h-5 w-5',
  default: 'h-8 w-8',
  full: 'h-10 w-10',
}

const TITLE_CLASSES: Record<NonNullable<EmptyStateProps['size']>, string> = {
  compact: 'text-xs font-semibold text-fg-muted',
  default: 'text-sm font-semibold text-fg-muted',
  full: 'text-lg font-semibold text-fg',
}

const DESCRIPTION_CLASSES: Record<NonNullable<EmptyStateProps['size']>, string> = {
  compact: 'mt-1 max-w-sm text-xs text-fg-subtle',
  default: 'mt-1 max-w-sm text-xs text-fg-subtle',
  full: 'mt-2 max-w-md text-sm text-fg-subtle',
}

function EmptyStateContent({
  title = 'Nothing to show here yet',
  description,
  action,
  icon: Icon = InboxIcon,
  size = 'default',
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${SIZE_CLASSES[size]} ${className}`}
    >
      <div className={`rounded-full bg-surface ${ICON_WRAPPER_CLASSES[size]}`}>
        <Icon className={`${ICON_CLASSES[size]} text-fg-subtle`} aria-hidden="true" />
      </div>

      <h3 className={TITLE_CLASSES[size]}>{title}</h3>
      {description && <p className={DESCRIPTION_CLASSES[size]}>{description}</p>}

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

export default function EmptyState(props: EmptyStateProps) {
  if (props.size === 'full') {
    return (
      <FadeIn>
        <EmptyStateContent {...props} />
      </FadeIn>
    )
  }
  return <EmptyStateContent {...props} />
}
