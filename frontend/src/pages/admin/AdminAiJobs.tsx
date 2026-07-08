import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminAiJobRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function statusClass(status: string) {
  if (status === 'complete') return 'bg-chip-success text-chip-success-fg'
  if (status === 'failed') return 'bg-chip-danger text-chip-danger-fg'
  if (status === 'processing') return 'bg-chip-accent text-accent-text'
  return 'bg-track text-fg-muted'
}

export default function AdminAiJobs() {
  const [items, setItems] = useState<AdminAiJobRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchJobs = useCallback(() => {
    setLoading(true)
    adminApi
      .listAiJobs({
        kind: kind || undefined,
        status: status || undefined,
        search: search || undefined,
        page,
        size: PAGE_SIZE,
      })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load AI jobs'))
      .finally(() => setLoading(false))
  }, [kind, page, search, status])

  useEffect(() => {
    document.title = 'AI Jobs - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    setPage(1)
  }, [kind, status, search])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">AI Jobs</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Tailoring and cover-letter jobs across all users.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_180px_180px]">
          <input
            type="search"
            placeholder="Search email, company, or job title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm"
          >
            <option value="">All job types</option>
            <option value="tailor">Tailor</option>
            <option value="cover_letter">Cover letter</option>
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="complete">Complete</option>
            <option value="failed">Failed</option>
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
            <div className="py-12 text-center text-sm text-fg-subtle">No AI jobs found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line">
              <thead>
                <tr>
                  {['Type', 'Status', 'User', 'Target', 'Mode', 'Updated', 'Failure'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((job) => (
                  <tr key={`${job.kind}-${job.id}`} className="hover:bg-surface-strong">
                    <td className="px-4 py-3 text-sm font-medium text-fg">
                      {job.kind === 'tailor' ? 'Tailor' : 'Cover letter'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(job.status)}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-sm text-fg-muted">
                      {job.user_email ?? job.user_id}
                    </td>
                    <td className="max-w-[260px] px-4 py-3 text-sm text-fg">
                      <p className="truncate font-medium">{job.job_title ?? 'Untitled job'}</p>
                      <p className="truncate text-xs text-fg-subtle">{job.company_name ?? 'Unknown company'}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">
                      {job.intensity ?? job.tone ?? '-'}
                      {job.language ? ` / ${job.language}` : ''}
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">{formatDate(job.updated_at)}</td>
                    <td className="max-w-[300px] truncate px-4 py-3 text-xs text-chip-danger-fg">
                      {job.error_message ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>{total.toLocaleString()} jobs</span>
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
