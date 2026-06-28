import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import { LocationInput } from '../discover/JobFilters'

export type SearchSource = 'all' | 'adzuna' | 'platsbanken'

const SOURCE_OPTIONS: { value: SearchSource; label: string }[] = [
  { value: 'all', label: 'All Sources' },
  { value: 'adzuna', label: 'Adzuna' },
  { value: 'platsbanken', label: 'Platsbanken' },
]

interface Props {
  initialQuery?: string
  initialLocation?: string
  loading?: boolean
  source?: SearchSource
  onSourceChange?: (source: SearchSource) => void
  onSearch: (q: string, location: string) => void
}

export default function JobSearchBar({
  initialQuery = '',
  initialLocation = '',
  loading,
  source = 'all',
  onSourceChange,
  onSearch,
}: Props) {
  const [query, setQuery] = useState(initialQuery)
  const [location, setLocation] = useState(initialLocation)

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch(query.trim(), location.trim())
  }

  return (
    <div className="space-y-3">
      {onSourceChange && (
        <div className="flex gap-2">
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onSourceChange(opt.value)}
              className={[
                'rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors',
                source === opt.value
                  ? 'bg-brand-600 text-white'
                  : 'bg-surface text-fg-muted hover:bg-surface-strong hover:text-fg',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-line bg-surface p-4 shadow-sm"
      >
        <div className="grid gap-3 md:grid-cols-[1fr_260px_auto]">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input pl-9"
              placeholder="Role, skill, or keyword"
            />
          </div>
          <LocationInput value={location} onChange={setLocation} />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            <MagnifyingGlassIcon className="h-4 w-4" />
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>
    </div>
  )
}
