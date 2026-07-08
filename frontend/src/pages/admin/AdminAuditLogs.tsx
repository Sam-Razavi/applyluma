import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminAuditLogRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function details(value: Record<string, unknown>) {
  const text = JSON.stringify(value)
  return text === '{}' ? '-' : text
}

export default function AdminAuditLogs() {
  const [items, setItems] = useState<AdminAuditLogRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [userId, setUserId] = useState('')
  const [loading, setLoading] = useState(true)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchLogs = useCallback(() => {
    setLoading(true)
    adminApi
      .listAuditLogs({
        action: action || undefined,
        user_id: userId || undefined,
        page,
        size: PAGE_SIZE,
      })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load audit logs'))
      .finally(() => setLoading(false))
  }, [action, page, userId])

  useEffect(() => {
    document.title = 'Audit Logs - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    setPage(1)
  }, [action, userId])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Audit Logs</h1>
          <p className="mt-1 text-sm text-fg-subtle">History of admin actions recorded by the platform.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-[220px_1fr]">
          <select value={action} onChange={(e) => setAction(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">All actions</option>
            <option value="user.role_changed">Role changed</option>
            <option value="user.active_changed">Active changed</option>
            <option value="user.notification_sent">Notification sent</option>
          </select>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Filter by admin or target user UUID..."
            className="rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
          {loading ? (
            <div className="space-y-3 p-5">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-12 animate-pulse rounded-lg bg-track" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No audit logs found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line">
              <thead>
                <tr>
                  {['When', 'Action', 'Admin', 'Target', 'Details', 'IP'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-strong">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-fg-subtle">{formatDate(log.created_at)}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-fg">{log.action}</td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-sm text-fg-muted">{log.admin_email ?? log.admin_user_id ?? '-'}</td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-sm text-fg-muted">{log.target_email ?? log.target_user_id ?? '-'}</td>
                    <td className="max-w-[360px] truncate px-4 py-3 text-xs text-fg-subtle">{details(log.details)}</td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">{log.ip_address ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>{total.toLocaleString()} audit entries</span>
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
