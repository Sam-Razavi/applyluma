import { CSS } from '@dnd-kit/utilities'
import { useSortable } from '@dnd-kit/sortable'
import {
  Bars3Icon,
  BriefcaseIcon,
  CalendarDaysIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline'
import { useApplicationsStore } from '../../stores/applications'
import type { Application } from '../../types/application'

interface Props {
  application: Application
}

const priorityClasses: Record<number, string> = {
  1: 'bg-gray-100 text-gray-600',
  2: 'bg-amber-100 text-amber-700',
  3: 'bg-red-100 text-red-700',
}

const priorityLabels: Record<number, string> = {
  1: 'Low',
  2: 'Med',
  3: 'High',
}

function formatDate(value: string | null): string {
  if (!value) return 'Not applied'
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function ApplicationCard({ application }: Props) {
  const setSelected = useApplicationsStore((state) => state.setSelected)
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: application.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      onClick={() => setSelected(application)}
      className={`group rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-brand-200 hover:shadow-md ${
        isDragging ? 'opacity-70 ring-2 ring-brand-300' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <BriefcaseIcon className="h-5 w-5 text-brand-600" />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-gray-900">
            {application.job_title}
          </h3>
          <p className="truncate text-sm text-gray-500">{application.company_name}</p>
        </div>

        <button
          type="button"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
          aria-label={`Drag ${application.job_title}`}
          onClick={(event) => event.stopPropagation()}
          {...attributes}
          {...listeners}
        >
          <Bars3Icon className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
            priorityClasses[application.priority] ?? priorityClasses[1]
          }`}
        >
          {priorityLabels[application.priority] ?? 'Low'}
        </span>
        {application.source && (
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
            {application.source.replace('_', ' ')}
          </span>
        )}
      </div>

      <div className="mt-3 space-y-1.5 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <CalendarDaysIcon className="h-3.5 w-3.5 text-gray-400" />
          <span>{formatDate(application.applied_date)}</span>
        </div>
        {application.location && (
          <div className="flex items-center gap-1.5">
            <MapPinIcon className="h-3.5 w-3.5 text-gray-400" />
            <span className="truncate">{application.location}</span>
          </div>
        )}
      </div>
    </article>
  )
}
