import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'

interface Props {
  initialQuery?: string
  initialLocation?: string
  loading?: boolean
  onSearch: (q: string, location: string) => void
}

export default function JobSearchBar({
  initialQuery = '',
  initialLocation = '',
  loading,
  onSearch,
}: Props) {
  const [query, setQuery] = useState(initialQuery)
  const [location, setLocation] = useState(initialLocation)

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch(query.trim(), location.trim())
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="grid gap-3 md:grid-cols-[1fr_260px_auto]">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input pl-9"
            placeholder="Role, skill, or keyword"
          />
        </div>
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="input"
          placeholder="Location"
        />
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
  )
}
