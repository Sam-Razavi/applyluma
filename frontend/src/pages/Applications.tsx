import { useEffect, useMemo, useState } from 'react'
import {
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import AddApplicationModal from '../components/applications/AddApplicationModal'
import ApplicationDrawer from '../components/applications/ApplicationDrawer'
import ApplicationStats from '../components/applications/ApplicationStats'
import KanbanBoard from '../components/applications/KanbanBoard'
import { STATUS_META } from '../components/applications/applicationMeta'
import PersonalAnalytics from '../components/applications/PersonalAnalytics'
import { useApplicationsStore } from '../stores/applications'
import type { ApplicationStatus } from '../types/application'
import { APPLICATION_STATUSES } from '../types/application'

export default function Applications() {
  const applications = useApplicationsStore((state) => state.applications)
  const stats = useApplicationsStore((state) => state.stats)
  const isLoading = useApplicationsStore((state) => state.isLoading)
  const error = useApplicationsStore((state) => state.error)
  const filters = useApplicationsStore((state) => state.filters)
  const fetchApplications = useApplicationsStore((state) => state.fetchApplications)
  const setFilters = useApplicationsStore((state) => state.setFilters)
  const [addOpen, setAddOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'board' | 'stats'>('board')

  useEffect(() => {
    void fetchApplications()
  }, [fetchApplications])

  useEffect(() => {
    document.title = 'Applications | ApplyLuma'
  }, [])

  const filteredApplications = useMemo(() => {
    const search = filters.search.trim().toLowerCase()
    if (!search) return applications
    return applications.filter((application) =>
      [
        application.company_name,
        application.job_title,
        application.location ?? '',
        application.source ?? '',
      ].some((value) => value.toLowerCase().includes(search)),
    )
  }, [applications, filters.search])

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
          <p className="mt-1 text-sm text-gray-500">
            Track every opportunity from wishlist to offer.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 sm:self-auto"
        >
          <PlusIcon className="h-4 w-4" />
          Add Application
        </button>
      </div>

      <div className="flex rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
        {[
          { id: 'board', label: 'Board' },
          { id: 'stats', label: 'My Stats' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as 'board' | 'stats')}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.id
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'stats' ? (
        <PersonalAnalytics />
      ) : (
        <>
          <ApplicationStats stats={stats} />

          <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                value={filters.search}
                onChange={(e) => setFilters({ search: e.target.value })}
                placeholder="Search by company, role, location, or source..."
                className="w-full rounded-xl border border-gray-200 bg-white py-2.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <select
              value={filters.status}
              onChange={(e) => {
                setFilters({ status: e.target.value as ApplicationStatus | '' })
                queueMicrotask(() => void fetchApplications())
              }}
              className="rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All statuses</option>
              {APPLICATION_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {STATUS_META[status].label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {[...Array(6)].map((_, index) => (
                <div key={index} className="h-36 animate-pulse rounded-2xl bg-gray-100" />
              ))}
            </div>
          ) : filteredApplications.length === 0 ? (
            <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
              <h2 className="text-sm font-semibold text-gray-900">
                {filters.search ? 'No matching applications' : 'No applications yet'}
              </h2>
              <p className="mt-1 text-sm text-gray-400">
                {filters.search
                  ? 'Adjust the search or status filter to broaden the board.'
                  : 'Add your first application to start tracking your pipeline.'}
              </p>
              {!filters.search && (
                <button
                  type="button"
                  onClick={() => setAddOpen(true)}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 transition hover:text-brand-700"
                >
                  <PlusIcon className="h-4 w-4" />
                  Add an application
                </button>
              )}
            </div>
          ) : (
            <KanbanBoard applications={filteredApplications} />
          )}
        </>
      )}

      {activeTab === 'board' && (
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label="Add application"
        >
          <PlusIcon className="h-6 w-6" />
        </button>
      )}

      <AddApplicationModal open={addOpen} onClose={() => setAddOpen(false)} />
      <ApplicationDrawer />
    </div>
  )
}
