import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { exportApplicationsToCsv } from '../utils/exportCsv'
import AddApplicationModal from '../components/applications/AddApplicationModal'
import ApplicationDrawer from '../components/applications/ApplicationDrawer'
import ApplicationStats from '../components/applications/ApplicationStats'
import KanbanBoard from '../components/applications/KanbanBoard'
import PersonalAnalytics from '../components/applications/PersonalAnalytics'
import { STATUS_META } from '../components/applications/statusMeta'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { useApplicationsStore } from '../stores/applications'
import type { ApplicationStatus } from '../types/application'
import { APPLICATION_STATUSES } from '../types/application'

const STALE_DAYS = 14
const TERMINAL_STATUSES = new Set(['rejected', 'withdrawn'])

export default function Applications() {
  const applications = useApplicationsStore((state) => state.applications)
  const stats = useApplicationsStore((state) => state.stats)
  const isLoading = useApplicationsStore((state) => state.isLoading)
  const error = useApplicationsStore((state) => state.error)
  const filters = useApplicationsStore((state) => state.filters)
  const fetchApplications = useApplicationsStore((state) => state.fetchApplications)
  const setFilters = useApplicationsStore((state) => state.setFilters)
  const bulkDeleteApplications = useApplicationsStore((state) => state.bulkDeleteApplications)

  const [addOpen, setAddOpen] = useState(false)
  const [staleFilter, setStaleFilter] = useState(false)
  const [isSelectMode, setIsSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') === 'stats' ? 'stats' : 'board') as 'board' | 'stats'

  function setActiveTab(tab: 'board' | 'stats') {
    setSearchParams(tab === 'board' ? {} : { tab })
  }

  useEffect(() => {
    void fetchApplications()
  }, [fetchApplications])

  useEffect(() => {
    document.title = 'Applications | ApplyLuma'
  }, [])

  const staleThreshold = useMemo(() => Date.now() - STALE_DAYS * 86_400_000, [])

  const staleCount = useMemo(
    () =>
      applications.filter(
        (app) =>
          !TERMINAL_STATUSES.has(app.status) &&
          new Date(app.updated_at).getTime() < staleThreshold,
      ).length,
    [applications, staleThreshold],
  )

  const filteredApplications = useMemo(() => {
    let result = applications
    const search = filters.search.trim().toLowerCase()
    if (search) {
      result = result.filter((application) =>
        [
          application.company_name,
          application.job_title,
          application.location ?? '',
          application.source ?? '',
        ].some((value) => value.toLowerCase().includes(search)),
      )
    }
    if (staleFilter) {
      result = result.filter(
        (app) =>
          !TERMINAL_STATUSES.has(app.status) &&
          new Date(app.updated_at).getTime() < staleThreshold,
      )
    }
    return result
  }, [applications, filters.search, staleFilter, staleThreshold])

  const todayCount = useMemo(() => {
    const startOfToday = new Date()
    startOfToday.setHours(0, 0, 0, 0)
    return applications.filter((a) => new Date(a.created_at) >= startOfToday).length
  }, [applications])

  function toggleSelectMode() {
    setIsSelectMode((prev) => !prev)
    setSelectedIds(new Set())
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleBulkDelete() {
    setDeleteConfirmOpen(true)
  }

  async function confirmBulkDelete() {
    const count = selectedIds.size
    if (count === 0) return
    setBulkDeleting(true)
    try {
      await bulkDeleteApplications([...selectedIds])
      setSelectedIds(new Set())
      setIsSelectMode(false)
      setDeleteConfirmOpen(false)
    } finally {
      setBulkDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-fg">Applications</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Track every opportunity from wishlist to offer.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          {applications.length > 0 && !isSelectMode && (
            <button
              type="button"
              onClick={() => exportApplicationsToCsv(applications)}
              className="inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 py-2.5 text-sm font-semibold text-fg-muted transition hover:bg-surface-strong"
              title="Export all applications to CSV"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Export CSV
            </button>
          )}
          {applications.length > 0 && activeTab === 'board' && (
            <button
              type="button"
              onClick={toggleSelectMode}
              className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition ${
                isSelectMode
                  ? 'border-chip-danger bg-chip-danger text-chip-danger-fg hover:bg-chip-danger'
                  : 'border-line-strong bg-surface text-fg-muted hover:bg-surface-strong'
              }`}
            >
              {isSelectMode ? (
                <>
                  <XMarkIcon className="h-4 w-4" />
                  Cancel
                </>
              ) : (
                <>
                  <CheckCircleIcon className="h-4 w-4" />
                  Select
                </>
              )}
            </button>
          )}
          {!isSelectMode && (
            <button
              type="button"
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              <PlusIcon className="h-4 w-4" />
              Add Application
            </button>
          )}
        </div>
      </div>

      <div className="flex rounded-xl border border-line bg-surface p-1 shadow-sm">
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
                : 'text-fg-subtle hover:bg-surface-strong hover:text-fg'
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
          {todayCount > 0 && (
            <p className="text-xs text-fg-muted">
              <span className="font-semibold text-fg">{todayCount}</span> added today
            </p>
          )}
          <ApplicationStats stats={stats} />

          <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={filters.search}
                onChange={(e) => setFilters({ search: e.target.value })}
                placeholder="Search by company, role, location, or source..."
                className="w-full rounded-xl border border-line bg-surface py-2.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={filters.status}
                onChange={(e) => {
                  setFilters({ status: e.target.value as ApplicationStatus | '' })
                  queueMicrotask(() => void fetchApplications())
                }}
                className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">All statuses</option>
                {APPLICATION_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STATUS_META[status].label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setStaleFilter((prev) => !prev)}
                className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-2.5 text-sm font-semibold transition ${
                  staleFilter
                    ? 'border-amber-400 bg-chip-warn text-chip-warn-fg'
                    : 'border-line bg-surface text-fg-subtle hover:bg-surface-strong hover:text-fg-muted'
                }`}
                title={`Show applications with no activity in ${STALE_DAYS}+ days`}
              >
                <ClockIcon className="h-4 w-4" />
                Stale
                {staleCount > 0 && (
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-xs font-bold ${
                      staleFilter ? 'bg-amber-200 text-chip-warn-fg' : 'bg-surface text-fg-muted'
                    }`}
                  >
                    {staleCount}
                  </span>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-chip-danger bg-chip-danger px-4 py-3 text-sm text-chip-danger-fg">
              <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
              {error}
            </div>
          )}

          {isSelectMode && (
            <div className="flex items-center gap-2 rounded-xl border border-primary-600/30 bg-primary-900/20 px-4 py-3 text-sm text-accent-text">
              <CheckCircleIcon className="h-4 w-4 flex-shrink-0" />
              Click cards to select them, then use the action bar to delete.
            </div>
          )}

          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {[...Array(6)].map((_, index) => (
                <div key={index} className="h-36 animate-pulse rounded-2xl bg-track" />
              ))}
            </div>
          ) : filteredApplications.length === 0 ? (
            <div className="rounded-2xl border border-line bg-surface px-6 py-16 text-center">
              <h2 className="text-sm font-semibold text-fg">
                {staleFilter
                  ? 'No stale applications'
                  : filters.search
                    ? 'No matching applications'
                    : 'No applications yet'}
              </h2>
              <p className="mt-1 text-sm text-fg-subtle">
                {staleFilter
                  ? `All active applications have had activity in the last ${STALE_DAYS} days.`
                  : filters.search
                    ? 'Adjust the search or status filter to broaden the board.'
                    : 'Add your first application to start tracking your pipeline.'}
              </p>
              {!filters.search && !staleFilter && (
                <button
                  type="button"
                  onClick={() => setAddOpen(true)}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-accent-text transition hover:text-accent-text"
                >
                  <PlusIcon className="h-4 w-4" />
                  Add an application
                </button>
              )}
            </div>
          ) : (
            <KanbanBoard
              applications={filteredApplications}
              isSelectMode={isSelectMode}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
            />
          )}
        </>
      )}

      {activeTab === 'board' && !isSelectMode && (
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label="Add application"
        >
          <PlusIcon className="h-6 w-6" />
        </button>
      )}

      {/* Bulk action bar */}
      {isSelectMode && selectedIds.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-line bg-surface px-4 py-4 shadow-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <span className="text-sm font-semibold text-fg-muted">
              {selectedIds.size} application{selectedIds.size > 1 ? 's' : ''} selected
            </span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                className="text-sm text-fg-subtle hover:text-fg-muted"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
              >
                <TrashIcon className="h-4 w-4" />
                {bulkDeleting ? 'Deleting…' : `Delete ${selectedIds.size}`}
              </button>
            </div>
          </div>
        </div>
      )}

      <AddApplicationModal open={addOpen} onClose={() => setAddOpen(false)} />
      <ApplicationDrawer />
      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete Application"
        message={`Permanently delete ${selectedIds.size} application${selectedIds.size === 1 ? '' : 's'}? This cannot be undone.`}
        loading={bulkDeleting}
        onCancel={() => setDeleteConfirmOpen(false)}
        onConfirm={() => void confirmBulkDelete()}
      />
    </div>
  )
}
