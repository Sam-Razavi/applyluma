import { useState } from 'react'
import { ChevronDownIcon, FunnelIcon, XMarkIcon } from '@heroicons/react/24/outline'
import type { JobFilters } from '../../types/jobDiscovery'
import { JOB_SOURCES, SOURCE_LABELS } from '../../types/jobDiscovery'

interface Props {
  filters: JobFilters
  onChange: (filters: JobFilters) => void
  onReset: () => void
}

const SORT_OPTIONS = [
  { value: 'score_desc', label: 'Best match' },
  { value: 'salary_desc', label: 'Highest salary' },
  { value: 'date_posted', label: 'Most recent' },
]

function hasActiveFilters(f: JobFilters): boolean {
  return (
    !!f.location ||
    !!f.salary_min ||
    !!f.salary_max ||
    !!f.keywords ||
    !!f.source ||
    f.remote_only ||
    !!f.match_score_min
  )
}

export default function JobFilters({ filters, onChange, onReset }: Props) {
  const [mobileOpen, setMobileOpen] = useState(false)

  function set(key: keyof JobFilters, value: string | boolean) {
    onChange({ ...filters, [key]: value })
  }

  const active = hasActiveFilters(filters)

  return (
    <aside className="w-full rounded-2xl border border-white/10 bg-white/[0.04] lg:w-64 lg:shrink-0">
      {/* Header — always visible, toggles body on mobile */}
      <div className="flex items-center justify-between p-5">
        <button
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          className="flex items-center gap-1.5 text-sm font-semibold text-white/90 lg:cursor-default"
          aria-expanded={mobileOpen}
        >
          <FunnelIcon className="h-4 w-4" />
          Filters
          {active && (
            <span className="ml-1 rounded-full bg-primary-100 px-1.5 py-0.5 text-xs font-medium text-primary-400 lg:hidden">
              On
            </span>
          )}
          <ChevronDownIcon
            className={`h-4 w-4 text-white/30 transition-transform lg:hidden ${mobileOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {active && (
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1 text-xs text-white/30 hover:text-white/55"
          >
            <XMarkIcon className="h-3.5 w-3.5" />
            Reset
          </button>
        )}
      </div>

      <div className={`space-y-4 px-5 pb-5 ${mobileOpen ? 'block' : 'hidden'} lg:block`}>
        {/* Sort */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">Sort by</label>
          <select
            value={filters.sort}
            onChange={(e) => set('sort', e.target.value)}
            className="w-full rounded-lg border border-white/15 bg-white/[0.04] px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Location */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">Location</label>
          <input
            type="text"
            value={filters.location}
            onChange={(e) => set('location', e.target.value)}
            placeholder="e.g. Stockholm"
            className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm placeholder-white/30 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        {/* Salary range */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">Salary (kr/month)</label>
          <div className="flex gap-2">
            <input
              type="number"
              value={filters.salary_min}
              onChange={(e) => set('salary_min', e.target.value)}
              placeholder="Min"
              min={0}
              className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm placeholder-white/30 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <input
              type="number"
              value={filters.salary_max}
              onChange={(e) => set('salary_max', e.target.value)}
              placeholder="Max"
              min={0}
              className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm placeholder-white/30 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Keywords */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">Keywords</label>
          <input
            type="text"
            value={filters.keywords}
            onChange={(e) => set('keywords', e.target.value)}
            placeholder="Python, React, Docker…"
            className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm placeholder-white/30 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <p className="mt-1 text-xs text-white/30">Comma-separated</p>
        </div>

        {/* Source */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">Source</label>
          <select
            value={filters.source}
            onChange={(e) => set('source', e.target.value)}
            className="w-full rounded-lg border border-white/15 bg-white/[0.04] px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">All sources</option>
            {JOB_SOURCES.map((s) => (
              <option key={s} value={s}>
                {SOURCE_LABELS[s]}
              </option>
            ))}
          </select>
        </div>

        {/* Remote only */}
        <label className="flex items-center gap-3 rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-white/75">
          <input
            type="checkbox"
            checked={filters.remote_only}
            onChange={(e) => set('remote_only', e.target.checked)}
            className="h-4 w-4 rounded border-white/20 text-primary-500 focus:ring-primary-500"
          />
          Remote only
        </label>

        {/* Match score */}
        <div>
          <label className="mb-1 block text-xs font-medium text-white/55">
            Min match score
          </label>
          <input
            type="number"
            value={filters.match_score_min}
            onChange={(e) => set('match_score_min', e.target.value)}
            placeholder="e.g. 70"
            min={0}
            max={100}
            className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm placeholder-white/30 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>
    </aside>
  )
}
