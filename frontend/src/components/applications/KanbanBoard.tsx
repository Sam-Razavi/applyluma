import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import KanbanColumn from './KanbanColumn'
import type { Application, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import { useApplicationsStore } from '../../stores/applications'

interface Props {
  applications?: Application[]
}

export const STATUS_META: Record<ApplicationStatus, { label: string; color: string }> = {
  wishlist: { label: 'Wishlist', color: 'bg-gray-400' },
  applied: { label: 'Applied', color: 'bg-blue-500' },
  phone_screen: { label: 'Phone Screen', color: 'bg-yellow-500' },
  interview: { label: 'Interview', color: 'bg-purple-500' },
  offer: { label: 'Offer', color: 'bg-green-500' },
  rejected: { label: 'Rejected', color: 'bg-red-500' },
  withdrawn: { label: 'Withdrawn', color: 'bg-slate-500' },
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

export default function KanbanBoard({ applications: providedApplications }: Props) {
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
      <div className="space-y-3 md:hidden">
        {APPLICATION_STATUSES.map((status) => {
          const statusApplications = grouped[status]
          const isOpen = openStatuses.has(status)
          const ToggleIcon = isOpen ? ChevronUpIcon : ChevronDownIcon

          return (
            <section key={status} className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
              <button
                type="button"
                onClick={() => toggleStatus(status)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${STATUS_META[status].color}`} />
                  <span className="truncate text-sm font-semibold text-gray-800">
                    {STATUS_META[status].label}
                  </span>
                </span>
                <span className="flex flex-shrink-0 items-center gap-2">
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">
                    {statusApplications.length}
                  </span>
                  <ToggleIcon className="h-4 w-4 text-gray-400" />
                </span>
              </button>

              {isOpen && (
                <div className="space-y-3 border-t border-gray-100 bg-gray-50 p-3">
                  {statusApplications.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-gray-300 bg-white px-4 py-6 text-center text-xs text-gray-400">
                      No applications
                    </div>
                  ) : (
                    statusApplications.map((application) => (
                      <button
                        key={application.id}
                        type="button"
                        onClick={() => setSelected(application)}
                        className="block w-full rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm"
                      >
                        <span className="block truncate text-sm font-semibold text-gray-900">
                          {application.job_title}
                        </span>
                        <span className="mt-1 block truncate text-sm text-gray-500">
                          {application.company_name}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </section>
          )
        })}
      </div>

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
                />
              ))}
            </div>
          </div>
        </DndContext>
      </div>
    </>
  )
}
