import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import KanbanColumn from './KanbanColumn'
import type { Application, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import { useApplicationsStore } from '../../stores/applications'
import { STATUS_META } from './statusMeta'

interface Props {
  applications?: Application[]
  isSelectMode?: boolean
  selectedIds?: Set<string>
  onToggleSelect?: (id: string) => void
}

function isStatus(value: string): value is ApplicationStatus {
  return APPLICATION_STATUSES.includes(value as ApplicationStatus)
}

function groupByStatus(applications: Application[]): Record<ApplicationStatus, Application[]> {
  return APPLICATION_STATUSES.reduce(
    (groups, status) => ({
      ...groups,
      [status]: applications.filter((application) => application.status === status),
    }),
    {} as Record<ApplicationStatus, Application[]>,
  )
}

export default function KanbanBoard({
  applications: providedApplications,
  isSelectMode,
  selectedIds,
  onToggleSelect,
}: Props) {
  const storeApplications = useApplicationsStore((state) => state.applications)
  const updateApplication = useApplicationsStore((state) => state.updateApplication)
  const setSelected = useApplicationsStore((state) => state.setSelected)
  const [openStatuses, setOpenStatuses] = useState<Set<ApplicationStatus>>(
    () => new Set(APPLICATION_STATUSES),
  )
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))
  const applications = providedApplications ?? storeApplications
  const grouped = groupByStatus(applications)

  async function handleDragEnd(event: DragEndEvent) {
    if (isSelectMode) return
    const activeId = String(event.active.id)
    const overId = event.over?.id ? String(event.over.id) : ''
    if (!overId) return

    const activeApplication = applications.find((application) => application.id === activeId)
    if (!activeApplication) return

    const overApplication = applications.find((application) => application.id === overId)
    const nextStatus = isStatus(overId) ? overId : overApplication?.status
    if (!nextStatus || nextStatus === activeApplication.status) return

    await updateApplication(activeApplication.id, { status: nextStatus })
  }

  function toggleStatus(status: ApplicationStatus) {
    setOpenStatuses((current) => {
      const next = new Set(current)
      if (next.has(status)) next.delete(status)
      else next.add(status)
      return next
    })
  }

  return (
    <>
      {/* Mobile accordion view */}
      <div className="space-y-3 md:hidden">
        {APPLICATION_STATUSES.map((status) => {
          const statusApplications = grouped[status]
          const isOpen = openStatuses.has(status)
          const ToggleIcon = isOpen ? ChevronUpIcon : ChevronDownIcon

          return (
            <section key={status} className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]">
              <button
                type="button"
                onClick={() => toggleStatus(status)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${STATUS_META[status].color}`} />
                  <span className="truncate text-sm font-semibold text-white/90">
                    {STATUS_META[status].label}
                  </span>
                </span>
                <span className="flex flex-shrink-0 items-center gap-2">
                  <span className="rounded-full bg-white/[0.04] px-2 py-0.5 text-xs font-semibold text-white/55">
                    {statusApplications.length}
                  </span>
                  <ToggleIcon className="h-4 w-4 text-white/30" />
                </span>
              </button>

              {isOpen && (
                <div className="space-y-3 border-t border-white/10 bg-white/[0.03] p-3">
                  {statusApplications.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.04] px-4 py-6 text-center text-xs text-white/30">
                      No applications
                    </div>
                  ) : (
                    statusApplications.map((application) => (
                      <div
                        key={application.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => {
                          if (isSelectMode) {
                            onToggleSelect?.(application.id)
                          } else {
                            setSelected(application)
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            if (isSelectMode) onToggleSelect?.(application.id)
                            else setSelected(application)
                          }
                        }}
                        className={`flex items-center gap-3 rounded-xl border bg-white/[0.04] p-4 text-left shadow-sm transition cursor-pointer ${
                          isSelectMode && selectedIds?.has(application.id)
                            ? 'border-primary-500/50 ring-2 ring-primary-600/30'
                            : 'border-white/10 hover:border-primary-600/40'
                        }`}
                      >
                        {isSelectMode && (
                          <input
                            type="checkbox"
                            checked={selectedIds?.has(application.id) ?? false}
                            onChange={() => onToggleSelect?.(application.id)}
                            onClick={(e) => e.stopPropagation()}
                            className="h-4 w-4 flex-shrink-0 rounded border-white/15 text-primary-400 focus:ring-brand-500"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-white/90">
                            {application.job_title}
                          </span>
                          <span className="mt-1 block truncate text-sm text-white/30">
                            {application.company_name}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </section>
          )
        })}
      </div>

      {/* Desktop kanban view */}
      <div className="hidden md:block">
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <div className="-mx-4 overflow-x-auto px-4 pb-2">
            <div className="flex min-w-max gap-4">
              {APPLICATION_STATUSES.map((status) => (
                <KanbanColumn
                  key={status}
                  status={status}
                  label={STATUS_META[status].label}
                  colorClass={STATUS_META[status].color}
                  applications={grouped[status]}
                  isSelectMode={isSelectMode}
                  selectedIds={selectedIds}
                  onToggleSelect={onToggleSelect}
                />
              ))}
            </div>
          </div>
        </DndContext>
      </div>
    </>
  )
}
