import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type ContactSubmissionRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function statusClass(status: string) {
  if (status === 'new') return 'bg-chip-accent text-accent-text'
  if (status === 'replied') return 'bg-chip-success text-chip-success-fg'
  if (status === 'archived') return 'bg-track text-fg-muted'
  return 'bg-surface-strong text-fg-muted'
}

export default function AdminContactInbox() {
  const [items, setItems] = useState<ContactSubmissionRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchSubmissions = useCallback(() => {
    setLoading(true)
    adminApi
      .listContactSubmissions({ search: search || undefined, status: status || undefined, page, size: PAGE_SIZE })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load contact submissions'))
      .finally(() => setLoading(false))
  }, [page, search, status])

  useEffect(() => {
    document.title = 'Contact Inbox - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchSubmissions()
  }, [fetchSubmissions])

  useEffect(() => {
    setPage(1)
  }, [search, status])

  async function updateStatus(id: string, nextStatus: string) {
    try {
      const updated = await adminApi.updateContactSubmissionStatus(id, nextStatus)
      setItems((prev) => prev.map((item) => (item.id === id ? updated : item)))
      toast.success('Status updated')
    } catch {
      toast.error('Failed to update status')
    }
  }

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Contact Inbox</h1>
          <p className="mt-1 text-sm text-fg-subtle">Messages submitted through the public contact form.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email, subject, or message..." className="rounded-lg border border-line-strong px-3 py-2 text-sm" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="read">Read</option>
            <option value="replied">Replied</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        <div className="overflow-hidden rounded-2xl border border-line bg-surface">
          {loading ? (
            <div className="space-y-3 p-5">{[...Array(5)].map((_, i) => <div key={i} className="h-20 animate-pulse rounded-lg bg-track" />)}</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No contact submissions found.</div>
          ) : (
            <div className="divide-y divide-line">
              {items.map((item) => (
                <article key={item.id} className="p-5 hover:bg-surface-strong">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="truncate text-base font-semibold text-fg">{item.subject || 'No subject'}</h2>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(item.status)}`}>{item.status}</span>
                        {item.category && item.category !== 'contact' && (
                          <span className="rounded-full bg-chip-accent px-2.5 py-1 text-xs font-semibold text-accent-text">
                            {item.category}
                          </span>
                        )}
                        <span className="rounded-full bg-surface-strong px-2.5 py-1 text-xs font-medium text-fg-subtle">
                          {item.source === 'in_app' ? 'In-app' : 'Contact form'}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-fg-subtle">
                        {item.name} · <a href={`mailto:${item.email}`} className="text-accent-text hover:underline">{item.email}</a> · {formatDate(item.created_at)}
                      </p>
                    </div>
                    <select value={item.status} onChange={(e) => updateStatus(item.id, e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
                      <option value="new">New</option>
                      <option value="read">Read</option>
                      <option value="replied">Replied</option>
                      <option value="archived">Archived</option>
                    </select>
                  </div>
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-fg-muted">{item.message}</p>
                  <p className="mt-3 text-xs text-fg-subtle">
                    IP: {item.remote_ip ?? '-'} · User agent: {item.user_agent ?? '-'}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>{total.toLocaleString()} messages</span>
            <div className="flex items-center gap-2">
              <button className="rounded-lg border border-line-strong px-3 py-1.5 disabled:opacity-40" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button>
              <span>Page {page} of {totalPages}</span>
              <button className="rounded-lg border border-line-strong px-3 py-1.5 disabled:opacity-40" disabled={page === totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</button>
            </div>
          </div>
        )}
      </div>
    </FadeIn>
  )
}
