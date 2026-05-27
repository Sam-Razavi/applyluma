import { useState } from 'react'
import { CSS } from '@dnd-kit/utilities'
import { useSortable } from '@dnd-kit/sortable'
import {
  ArrowTopRightOnSquareIcon,
  BanknotesIcon,
  Bars3Icon,
  BriefcaseIcon,
  CalendarDaysIcon,
  ClockIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline'
import { useApplicationsStore } from '../../stores/applications'
import type { Application, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import { STATUS_META } from './statusMeta'

interface Props {
  application: Application
  isSelectMode?: boolean
  isSelected?: boolean
  onToggleSelect?: (id: string) => void
}

const STATUS_BADGE: Record<ApplicationStatus, string> = {
  wishlist: 'bg-gray-100 text-gray-700',
  applied: 'bg-blue-50 text-blue-700',
  phone_screen: 'bg-yellow-50 text-yellow-700',
  interview: 'bg-purple-50 text-purple-700',
  offer: 'bg-green-50 text-green-700',
  rejected: 'bg-red-50 text-red-700',
  withdrawn: 'bg-slate-100 text-slate-600',
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

function formatSalary(min: number | null, max: number | null): string | null {
  if (!min && !max) return null
  const fmt = (n: number) => n >= 1000 ? `${Math.round(n / 1000)}k` : String(n)
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return `${fmt(min)}+`
  return `up to ${fmt(max!)}`
}

function ageLabel(createdAt: string): string {
  const days = Math.floor((Date.now() - new Date(createdAt).getTime()) / 86_400_000)
  if (days === 0) return 'today'
  if (days === 1) return '1d'
  return `${days}d`
}

function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000)
}

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000)
}

const FOLLOWUP_STATUSES = new Set(['applied', 'phone_screen'])
const TERMINAL_STATUSES = new Set(['rejected', 'withdrawn', 'offer'])

export default function ApplicationCard({ application, isSelectMode, isSelected, onToggleSelect }: Props) {
  const setSelected = useApplicationsStore((state) => state.setSelected)
  const updateApplication = useApplicationsStore((state) => state.updateApplication)
  const [updatingStatus, setUpdatingStatus] = useState(false)

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: application.id })

  const days = daysSince(application.applied_date)
  const showNudge = FOLLOWUP_STATUSES.has(application.status) && days !== null && days >= 7
  const nudgeUrgent = days !== null && days >= 14

  const deadlineDays = daysUntil(application.deadline)
  const showDeadline = deadlineDays !== null && deadlineDays <= 3 && !TERMINAL_STATUSES.has(application.status)
  const deadlineLabel =
    deadlineDays === 0 ? 'Deadline today' :
    deadlineDays === 1 ? 'Deadline tomorrow' :
    deadlineDays !== null && deadlineDays < 0 ? 'Deadline passed' :
    `Deadline in ${deadlineDays} days`
  const deadlineClass =
    deadlineDays !== null && deadlineDays <= 1 ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'

  const salary = formatSalary(application.salary_min, application.salary_max)
  const age = ageLabel(application.created_at)

  async function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    e.stopPropagation()
    const newStatus = e.target.value as ApplicationStatus
    if (newStatus === application.status || updatingStatus) return
    setUpdatingStatus(true)
    try {
      await updateApplication(application.id, { status: newStatus })
    } finally {
      setUpdatingStatus(false)
    }
  }

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      onClick={() => {
        if (isSelectMode) {
          onToggleSelect?.(application.id)
        } else {
          setSelected(application)
        }
      }}
      className={`group relative rounded-xl border bg-white p-4 shadow-sm transition ${
        isSelectMode
          ? isSelected
            ? 'cursor-pointer border-brand-400 ring-2 ring-brand-200'
            : 'cursor-pointer border-gray-200 hover:border-brand-200'
          : `border-gray-200 hover:border-brand-200 hover:shadow-md ${isDragging ? 'opacity-70 ring-2 ring-brand-300' : ''}`
      }`}
    >
      {/* Selection checkbox */}
      {isSelectMode && (
        <div className="absolute left-3 top-3 z-10">
          <input
            type="checkbox"
            checked={isSelected ?? false}
            onChange={() => onToggleSelect?.(application.id)}
            onClick={(e) => e.stopPropagation()}
            className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
          />
        </div>
      )}

      <div className={`flex items-start gap-3 ${isSelectMode ? 'pl-6' : ''}`}>
        <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <BriefcaseIcon className="h-5 w-5 text-brand-600" />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-gray-900">
            {application.job_title}
          </h3>
          <p className="truncate text-sm text-gray-500">{application.company_name}</p>
        </div>

        {!isSelectMode && (
          <div className="flex shrink-0 items-center">
            {application.job_url && (
              <a
                href={application.job_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-brand-600"
                aria-label="Open job listing"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              </a>
            )}
            <button
              type="button"
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label={`Drag ${application.job_title}`}
              onClick={(e) => e.stopPropagation()}
              {...attributes}
              {...listeners}
            >
              <Bars3Icon className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Chips row: priority, source, age */}
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
        <span className="ml-auto flex items-center gap-1 text-xs text-gray-400">
          <ClockIcon className="h-3 w-3" />
          {age}
        </span>
      </div>

      {/* Info rows */}
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
        {salary && (
          <div className="flex items-center gap-1.5">
            <BanknotesIcon className="h-3.5 w-3.5 text-gray-400" />
            <span>{salary}</span>
          </div>
        )}
      </div>

      {showDeadline && (
        <div className={`mt-3 rounded-lg px-2.5 py-1.5 text-xs font-medium ${deadlineClass}`}>
          🗓 {deadlineLabel}
        </div>
      )}

      {showNudge && (
        <div
          className={`mt-3 rounded-lg px-2.5 py-1.5 text-xs font-medium ${
            nudgeUrgent ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
          }`}
        >
          {nudgeUrgent ? '⚠️' : '💬'} {days}d since applied — consider following up
        </div>
      )}

      {/* Quick status change */}
      {!isSelectMode && (
        <div className="mt-3 border-t border-gray-100 pt-2">
          <select
            value={application.status}
            onChange={handleStatusChange}
            onClick={(e) => e.stopPropagation()}
            disabled={updatingStatus}
            className={`w-full cursor-pointer rounded-lg border-0 py-1 pl-2 pr-6 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-brand-400 disabled:cursor-not-allowed disabled:opacity-60 ${STATUS_BADGE[application.status]}`}
            aria-label="Change status"
          >
            {APPLICATION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {STATUS_META[status].label}
              </option>
            ))}
          </select>
        </div>
      )}
    </article>
  )
}
