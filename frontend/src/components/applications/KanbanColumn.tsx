import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import ApplicationCard from './ApplicationCard'
import type { Application, ApplicationStatus } from '../../types/application'

interface Props {
  status: ApplicationStatus
  label: string
  colorClass: string
  applications: Application[]
}

export default function KanbanColumn({ status, label, colorClass, applications }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <section
      ref={setNodeRef}
      className={`flex h-auto min-h-[18rem] w-72 flex-shrink-0 flex-col rounded-2xl border border-gray-200 bg-gray-50 transition md:h-[calc(100vh-17rem)] md:min-h-[28rem] ${
        isOver ? 'border-brand-300 bg-brand-50' : ''
      }`}
    >
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${colorClass}`} />
          <h2 className="text-sm font-semibold text-gray-800">{label}</h2>
        </div>
        <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-gray-500 shadow-sm">
          {applications.length}
        </span>
      </div>

      <SortableContext items={applications.map((application) => application.id)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 space-y-3 overflow-y-auto p-3">
          {applications.length === 0 ? (
            <div className="flex h-28 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white/70 px-4 text-center text-xs text-gray-400">
              Drop applications here
            </div>
          ) : (
            applications.map((application) => (
              <ApplicationCard key={application.id} application={application} />
            ))
          )}
        </div>
      </SortableContext>
    </section>
  )
}
