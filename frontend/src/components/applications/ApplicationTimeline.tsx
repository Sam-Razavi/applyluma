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
      <div className="rounded-xl border border-dashed border-gray-200 p-4 text-sm text-gray-400">
        No timeline events yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brand-50">
            <ClockIcon className="h-4 w-4 text-brand-600" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-gray-900">
                {formatEventType(event.event_type)}
              </p>
              <time className="flex-shrink-0 text-xs text-gray-400">
                {formatDate(event.event_date)}
              </time>
            </div>
            <p className="mt-0.5 text-sm text-gray-500">
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
