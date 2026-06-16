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

const BADGE_ACTIVE = 'bg-[rgba(8,145,178,0.15)] text-cyan-300 border border-[rgba(8,145,178,0.28)]'
const BADGE_SUCCESS = 'bg-[rgba(52,195,143,0.14)] text-emerald-300 border border-[rgba(52,195,143,0.22)]'
const BADGE_ERROR = 'bg-[rgba(229,72,77,0.12)] text-red-300 border border-[rgba(229,72,77,0.18)]'
const BADGE_NEUTRAL = 'bg-white/[0.06] text-white/55 border border-white/10'

const STATUS_BADGE: Record<ApplicationStatus, string> = {
  wishlist: BADGE_NEUTRAL,
  applied: BADGE_ACTIVE,
  phone_screen: BADGE_ACTIVE,
  interview: BADGE_ACTIVE,
  offer: BADGE_SUCCESS,
  rejected: BADGE_ERROR,
  withdrawn: BADGE_ERROR,
}

const priorityClasses: Record<number, string> = {
  1: BADGE_NEUTRAL,
  2: BADGE_ACTIVE,
  3: BADGE_ERROR,
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
    deadlineDays !== null && deadlineDays <= 1 ? 'bg-[rgba(229,72,77,0.12)] text-red-300' : 'bg-[rgba(245,158,11,0.14)] text-amber-300'

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
      className={`group relative rounded-xl border bg-white/[0.04] p-4 shadow-sm transition ${
        isSelectMode
          ? isSelected
            ? 'cursor-pointer border-primary-500/50 ring-2 ring-primary-600/30'
            : 'cursor-pointer border-white/10 hover:border-primary-600/40'
          : `border-white/10 hover:border-primary-600/40 hover:shadow-md ${isDragging ? 'opacity-70 ring-2 ring-primary-500/40' : ''}`
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
            className="h-4 w-4 rounded border-white/15 text-primary-400 focus:ring-brand-500"
          />
        </div>
      )}

      <div className={`flex items-start gap-3 ${isSelectMode ? 'pl-6' : ''}`}>
        <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary-900/20">
          <BriefcaseIcon className="h-5 w-5 text-primary-400" />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-white/90">
            {application.job_title}
          </h3>
          <p className="truncate text-sm text-white/30">{application.company_name}</p>
        </div>

        {!isSelectMode && (
          <div className="flex shrink-0 items-center">
            {application.job_url && (
              <a
                href={application.job_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-white/30 transition hover:bg-white/[0.06] hover:text-primary-300"
                aria-label="Open job listing"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              </a>
            )}
            <button
              type="button"
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-white/30 transition hover:bg-white/[0.06] hover:text-white/55"
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
          <span className="rounded-full bg-[rgba(8,145,178,0.15)] px-2 py-0.5 text-xs font-medium text-cyan-300">
            {application.source.replace('_', ' ')}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1 text-xs text-white/30">
          <ClockIcon className="h-3 w-3" />
          {age}
        </span>
      </div>

      {/* Info rows */}
      <div className="mt-3 space-y-1.5 text-xs text-white/30">
        <div className="flex items-center gap-1.5">
          <CalendarDaysIcon className="h-3.5 w-3.5 text-white/30" />
          <span>{formatDate(application.applied_date)}</span>
        </div>
        {application.location && (
          <div className="flex items-center gap-1.5">
            <MapPinIcon className="h-3.5 w-3.5 text-white/30" />
            <span className="truncate">{application.location}</span>
          </div>
        )}
        {salary && (
          <div className="flex items-center gap-1.5">
            <BanknotesIcon className="h-3.5 w-3.5 text-white/30" />
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
            nudgeUrgent ? 'bg-[rgba(229,72,77,0.12)] text-red-300' : 'bg-[rgba(245,158,11,0.14)] text-amber-300'
          }`}
        >
          {nudgeUrgent ? '⚠️' : '💬'} {days}d since applied — consider following up
        </div>
      )}

      {/* Quick status change */}
      {!isSelectMode && (
        <div className="mt-3 border-t border-white/10 pt-2">
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
