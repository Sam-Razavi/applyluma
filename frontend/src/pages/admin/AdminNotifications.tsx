import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminNotificationRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

export default function AdminNotifications() {
  const [items, setItems] = useState<AdminNotificationRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [audience, setAudience] = useState<'all' | 'role' | 'user'>('all')
  const [role, setRole] = useState('user')
  const [userId, setUserId] = useState('')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchMessages = useCallback(() => {
    setLoading(true)
    adminApi
      .listAdminNotifications({ search: search || undefined, page, size: PAGE_SIZE })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load admin messages'))
      .finally(() => setLoading(false))
  }, [page, search])

  useEffect(() => {
    document.title = 'Admin Notifications - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchMessages()
  }, [fetchMessages])

  useEffect(() => {
    setPage(1)
  }, [search])

  async function submitNotification() {
    setSubmitting(true)
    try {
      const result = await adminApi.sendBulkNotification({
        audience,
        role: audience === 'role' ? role : undefined,
        user_id: audience === 'user' ? userId : undefined,
        title,
        body,
        type: 'admin_message',
      })
      toast.success(`Sent ${result.sent_count.toLocaleString()} notifications`)
      setTitle('')
      setBody('')
      fetchMessages()
    } catch {
      toast.error('Failed to send notification')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Notification Center</h1>
          <p className="mt-1 text-sm text-fg-subtle">Send admin messages to users and review delivery history.</p>
        </div>

        <section className="rounded-2xl border border-line bg-surface p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">Send Message</h2>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <select value={audience} onChange={(e) => setAudience(e.target.value as typeof audience)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
              <option value="all">All active users</option>
              <option value="role">Role</option>
              <option value="user">Specific user</option>
            </select>
            {audience === 'role' ? (
              <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
                <option value="user">User</option>
                <option value="premium">Premium</option>
                <option value="admin">Admin</option>
              </select>
            ) : (
              <input value={userId} onChange={(e) => setUserId(e.target.value)} disabled={audience !== 'user'} placeholder="User UUID" className="rounded-lg border border-line-strong px-3 py-2 text-sm disabled:opacity-50" />
            )}
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" className="rounded-lg border border-line-strong px-3 py-2 text-sm" />
          </div>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} placeholder="Message body" className="mt-3 w-full resize-none rounded-lg border border-line-strong px-3 py-2 text-sm" />
          <div className="mt-3 flex justify-end">
            <button
              onClick={submitNotification}
              disabled={submitting || !title.trim() || !body.trim() || (audience === 'user' && !userId.trim())}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? 'Sending...' : 'Send Notification'}
            </button>
          </div>
        </section>

        <div className="flex items-center gap-3">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search sent messages..." className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm" />
        </div>

        <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
          {loading ? (
            <div className="space-y-3 p-5">{[...Array(5)].map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-track" />)}</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No admin messages found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line">
              <thead>
                <tr>{['Sent', 'Recipient', 'Title', 'Body', 'Read'].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-strong">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-fg-subtle">{formatDate(item.created_at)}</td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-sm text-fg-muted">{item.user_email ?? item.user_id}</td>
                    <td className="max-w-[260px] truncate px-4 py-3 text-sm font-medium text-fg">{item.title}</td>
                    <td className="max-w-[380px] truncate px-4 py-3 text-sm text-fg-subtle">{item.body}</td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{item.is_read ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
