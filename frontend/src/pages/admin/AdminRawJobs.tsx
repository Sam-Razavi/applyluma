import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type RawJobAdminRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

export default function AdminRawJobs() {
  const [items, setItems] = useState<RawJobAdminRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [duplicate, setDuplicate] = useState('')
  const [remote, setRemote] = useState('')
  const [loading, setLoading] = useState(true)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const sources = Array.from(new Set(items.map((item) => item.source))).sort()

  const fetchJobs = useCallback(() => {
    setLoading(true)
    adminApi
      .listRawJobs({
        search: search || undefined,
        source: source || undefined,
        duplicate: duplicate === '' ? undefined : duplicate === 'true',
        remote: remote === '' ? undefined : remote === 'true',
        page,
        size: PAGE_SIZE,
      })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load raw jobs'))
      .finally(() => setLoading(false))
  }, [duplicate, page, remote, search, source])

  useEffect(() => {
    document.title = 'Raw Jobs - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    setPage(1)
  }, [duplicate, remote, search, source])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Raw Job Postings</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Inspect scraped postings, duplicate flags, extracted keyword coverage, and matching coverage.
          </p>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr_160px_160px_160px]">
          <input
            type="search"
            placeholder="Search title, company, or location..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <select value={source} onChange={(e) => setSource(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">All sources</option>
            {sources.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select value={duplicate} onChange={(e) => setDuplicate(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">Any duplicate</option>
            <option value="true">Duplicate</option>
            <option value="false">Unique</option>
          </select>
          <select value={remote} onChange={(e) => setRemote(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">Any remote</option>
            <option value="true">Remote</option>
            <option value="false">Not remote</option>
          </select>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
          {loading ? (
            <div className="space-y-3 p-5">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-12 animate-pulse rounded-lg bg-track" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No raw jobs found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line">
              <thead>
                <tr>
                  {['Job', 'Source', 'Remote', 'Duplicate', 'Coverage', 'Scraped'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((job) => (
                  <tr key={job.id} className="hover:bg-surface-strong">
                    <td className="max-w-[360px] px-4 py-3">
                      <a href={job.url} target="_blank" rel="noreferrer" className="truncate text-sm font-semibold text-accent-text hover:underline">
                        {job.title}
                      </a>
                      <p className="truncate text-xs text-fg-subtle">{job.company} · {job.location ?? 'Unknown location'}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{job.source}</td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{job.is_remote || job.remote_allowed ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{job.is_duplicate ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">
                      {job.keyword_count} keywords · {job.saved_count} saves · {job.matching_score_count} scores
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">{formatDate(job.scraped_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>{total.toLocaleString()} postings</span>
            <div className="flex items-center gap-2">
              <button className="rounded-lg border border-line-strong px-3 py-1.5 disabled:opacity-40" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button className="rounded-lg border border-line-strong px-3 py-1.5 disabled:opacity-40" disabled={page === totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </FadeIn>
  )
}
