import { useState, useMemo } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import ApplicationCard from './ApplicationCard'
import type { Application, ApplicationStatus } from '../../types/application'

type SortKey = 'default' | 'date_desc' | 'date_asc' | 'priority' | 'company'

interface Props {
  status: ApplicationStatus
  label: string
  colorClass: string
  applications: Application[]
}

function sortApplications(apps: Application[], key: SortKey): Application[] {
  if (key === 'default') return apps
  return [...apps].sort((a, b) => {
    if (key === 'date_desc') return (b.applied_date ?? '').localeCompare(a.applied_date ?? '')
    if (key === 'date_asc') return (a.applied_date ?? '').localeCompare(b.applied_date ?? '')
    if (key === 'priority') return b.priority - a.priority
    if (key === 'company') return a.company_name.localeCompare(b.company_name)
    return 0
  })
}

export default function KanbanColumn({ status, label, colorClass, applications }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  const [sort, setSort] = useState<SortKey>('default')

  const sorted = useMemo(() => sortApplications(applications, sort), [applications, sort])

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
        <div className="flex items-center gap-1.5">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="rounded-md border border-gray-200 bg-white py-0.5 pl-1.5 pr-5 text-xs text-gray-500 shadow-sm focus:outline-none focus:ring-1 focus:ring-brand-400"
            aria-label="Sort column"
          >
            <option value="default">Default</option>
            <option value="date_desc">Newest first</option>
            <option value="date_asc">Oldest first</option>
            <option value="priority">Priority</option>
            <option value="company">Company A–Z</option>
          </select>
          <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-gray-500 shadow-sm">
            {applications.length}
          </span>
        </div>
      </div>

      <SortableContext items={sorted.map((application) => application.id)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 space-y-3 overflow-y-auto p-3">
          {sorted.length === 0 ? (
            <div className="flex h-28 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white/70 px-4 text-center text-xs text-gray-400">
              Drop applications here
            </div>
          ) : (
            sorted.map((application) => (
              <ApplicationCard key={application.id} application={application} />
            ))
          )}
        </div>
      </SortableContext>
    </section>
  )
}
