import { ClockIcon } from '@heroicons/react/24/outline'
import type { ApplicationEvent } from '../../types/application'

interface Props {
  events: ApplicationEvent[]
}

function formatEventType(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ApplicationTimeline({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line p-4 text-sm text-fg-muted">
        No timeline events yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary-900/20">
            <ClockIcon className="h-4 w-4 text-accent-text" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-sm font-medium text-fg">
                {formatEventType(event.event_type)}
              </p>
              <time className="flex-shrink-0 text-xs text-fg-muted">
                {formatDate(event.event_date)}
              </time>
            </div>
            <p className="mt-0.5 break-words text-sm text-fg-muted">
              {event.description ||
                [event.old_value, event.new_value].filter(Boolean).join(' -> ') ||
                'Application updated'}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
