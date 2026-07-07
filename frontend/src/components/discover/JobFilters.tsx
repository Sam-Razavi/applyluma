import { useEffect, useRef, useState } from 'react'
import { ChevronDownIcon, FunnelIcon, XMarkIcon } from '@heroicons/react/24/outline'
import type { JobFilters } from '../../types/jobDiscovery'
import { JOB_SOURCES, sourceLabel } from '../../types/jobDiscovery'
import { fetchJobSources } from '../../services/jobDiscoveryApi'

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

const LOCATION_SUGGESTIONS = [
  'Remote',
  'Stockholm', 'Göteborg', 'Malmö', 'Uppsala', 'Västerås',
  'Örebro', 'Linköping', 'Helsingborg', 'Jönköping', 'Norrköping',
  'Lund', 'Umeå', 'Gävle', 'Borås', 'Södertälje', 'Eskilstuna',
  'Halmstad', 'Växjö', 'Karlstad', 'Sundsvall', 'Östersund',
  'Skellefteå', 'Trollhättan', 'Kalmar', 'Falun',
]

const INPUT_CLS =
  'w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg ' +
  'placeholder:text-fg-subtle focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'

const SELECT_CLS =
  'w-full rounded-lg border border-line-strong bg-raised px-3 py-2 text-sm text-fg ' +
  'focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'

function hasActiveFilters(f: JobFilters): boolean {
  return (
    !!f.location ||
    !!f.salary_min ||
    !!f.salary_max ||
    !!f.keywords ||
    !!f.source ||
    f.remote_only ||
    f.hide_applied ||
    !!f.match_score_min
  )
}

interface LocationInputProps {
  value: string
  onChange: (v: string) => void
}

export function LocationInput({ value, onChange }: LocationInputProps) {
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)

  const suggestions = LOCATION_SUGGESTIONS.filter((l) =>
    value.length === 0 ? true : l.toLowerCase().includes(value.toLowerCase()),
  ).slice(0, 7)

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) {
      if (e.key === 'ArrowDown') { setOpen(true); setHighlighted(0) }
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault()
      onChange(suggestions[highlighted])
      setOpen(false)
      setHighlighted(-1)
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true); setHighlighted(-1) }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. Stockholm"
        className={INPUT_CLS}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
        role="combobox"
      />
      {open && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-lg border border-line py-1 shadow-xl"
          style={{ background: 'var(--nav-bg)', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)' }}
        >
          {suggestions.map((loc, i) => (
            <li
              key={loc}
              role="option"
              aria-selected={i === highlighted}
              onMouseDown={() => { onChange(loc); setOpen(false); setHighlighted(-1) }}
              onMouseEnter={() => setHighlighted(i)}
              className={`cursor-pointer px-3 py-2 text-sm transition-colors ${
                i === highlighted
                  ? 'bg-primary-900/40 text-[var(--accent-text)]'
                  : 'text-fg hover:bg-surface-strong'
              }`}
            >
              {loc}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function JobFilters({ filters, onChange, onReset }: Props) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [sources, setSources] = useState<readonly string[]>(JOB_SOURCES)

  useEffect(() => {
    let cancelled = false
    fetchJobSources()
      .then((rows) => {
        if (!cancelled && rows.length > 0) setSources(rows.map((r) => r.source))
      })
      .catch(() => {
        // Keep the static fallback list on error.
      })
    return () => {
      cancelled = true
    }
  }, [])

  function set(key: keyof JobFilters, value: string | boolean) {
    onChange({ ...filters, [key]: value })
  }

  const active = hasActiveFilters(filters)

  return (
    <aside className="w-full rounded-2xl border border-line bg-surface lg:w-64 lg:shrink-0">
      {/* Header — always visible, toggles body on mobile */}
      <div className="flex items-center justify-between p-5">
        <button
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          className="flex items-center gap-1.5 text-sm font-semibold text-fg lg:cursor-default"
          aria-expanded={mobileOpen}
        >
          <FunnelIcon className="h-4 w-4" />
          Filters
          {active && (
            <span className="ml-1 rounded-full bg-primary-100 px-1.5 py-0.5 text-xs font-medium text-accent-text lg:hidden">
              On
            </span>
          )}
          <ChevronDownIcon
            className={`h-4 w-4 text-fg-subtle transition-transform lg:hidden ${mobileOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {active && (
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1 text-xs text-fg-subtle hover:text-fg-muted"
          >
            <XMarkIcon className="h-3.5 w-3.5" />
            Reset
          </button>
        )}
      </div>

      <div className={`space-y-4 px-5 pb-5 ${mobileOpen ? 'block' : 'hidden'} lg:block`}>
        {/* Sort */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Sort by</label>
          <select
            value={filters.sort}
            onChange={(e) => set('sort', e.target.value)}
            className={SELECT_CLS}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Location with autocomplete */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Location</label>
          <LocationInput value={filters.location} onChange={(v) => set('location', v)} />
        </div>

        {/* Salary range */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Salary (kr/month)</label>
          <div className="flex gap-2">
            <input
              type="number"
              value={filters.salary_min}
              onChange={(e) => set('salary_min', e.target.value)}
              placeholder="Min"
              min={0}
              className={INPUT_CLS}
            />
            <input
              type="number"
              value={filters.salary_max}
              onChange={(e) => set('salary_max', e.target.value)}
              placeholder="Max"
              min={0}
              className={INPUT_CLS}
            />
          </div>
        </div>

        {/* Keywords */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Keywords</label>
          <input
            type="text"
            value={filters.keywords}
            onChange={(e) => set('keywords', e.target.value)}
            placeholder="Python, React, Docker…"
            className={INPUT_CLS}
          />
          <p className="mt-1 text-xs text-fg-subtle">Comma-separated</p>
        </div>

        {/* Source */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Source</label>
          <select
            value={filters.source}
            onChange={(e) => set('source', e.target.value)}
            className={SELECT_CLS}
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>{sourceLabel(s)}</option>
            ))}
          </select>
        </div>

        {/* Remote only */}
        <label className="flex items-center gap-3 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg">
          <input
            type="checkbox"
            checked={filters.remote_only}
            onChange={(e) => set('remote_only', e.target.checked)}
            className="h-4 w-4 rounded border-line-strong text-primary-500 focus:ring-primary-500"
          />
          Remote only
        </label>

        {/* Hide applied */}
        <label className="flex items-center gap-3 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-fg">
          <input
            type="checkbox"
            checked={filters.hide_applied}
            onChange={(e) => set('hide_applied', e.target.checked)}
            className="h-4 w-4 rounded border-line-strong text-primary-500 focus:ring-primary-500"
          />
          Hide applied jobs
        </label>

        {/* Match score */}
        <div>
          <label className="mb-1 block text-xs font-medium text-fg-muted">Min match score</label>
          <input
            type="number"
            value={filters.match_score_min}
            onChange={(e) => set('match_score_min', e.target.value)}
            placeholder="e.g. 70"
            min={0}
            max={100}
            className={INPUT_CLS}
          />
        </div>
      </div>
    </aside>
  )
}
