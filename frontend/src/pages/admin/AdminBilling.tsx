import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminBillingSummary, type AdminBillingUserRow } from '../../services/adminApi'

const PAGE_SIZE = 25

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-fg-subtle">{label}</p>
      <p className="mt-1 text-3xl font-bold text-fg">{value.toLocaleString()}</p>
    </div>
  )
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleDateString() : '-'
}

export default function AdminBilling() {
  const [items, setItems] = useState<AdminBillingUserRow[]>([])
  const [summary, setSummary] = useState<AdminBillingSummary | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchBilling = useCallback(() => {
    setLoading(true)
    adminApi
      .listBillingUsers({ search: search || undefined, status: status || undefined, page, size: PAGE_SIZE })
      .then((data) => {
        setItems(data.items)
        setTotal(data.total)
        setSummary(data.summary)
      })
      .catch(() => toast.error('Failed to load billing users'))
      .finally(() => setLoading(false))
  }, [page, search, status])

  useEffect(() => {
    document.title = 'Billing Admin - ApplyLuma'
  }, [])

  useEffect(() => {
    fetchBilling()
  }, [fetchBilling])

  useEffect(() => {
    setPage(1)
  }, [search, status])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Billing & Subscriptions</h1>
          <p className="mt-1 text-sm text-fg-subtle">Read-only subscription status and Stripe identifiers.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Users" value={summary?.total_users ?? 0} />
          <Stat label="Premium" value={summary?.premium_users ?? 0} />
          <Stat label="Active" value={summary?.active_subscriptions ?? 0} />
          <Stat label="Canceled" value={summary?.canceled_subscriptions ?? 0} />
          <Stat label="Past due" value={summary?.past_due_subscriptions ?? 0} />
        </div>

        <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search email or name..." className="rounded-lg border border-line-strong px-3 py-2 text-sm" />
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-line-strong px-3 py-2 text-sm">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="canceled">Canceled</option>
            <option value="past_due">Past due</option>
          </select>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
          {loading ? (
            <div className="space-y-3 p-5">{[...Array(5)].map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-track" />)}</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No billing users found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line">
              <thead>
                <tr>{['User', 'Role', 'Status', 'Ends', 'Stripe Customer', 'Stripe Subscription'].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-strong">
                    <td className="max-w-[260px] px-4 py-3">
                      <p className="truncate text-sm font-medium text-fg">{user.email}</p>
                      <p className="truncate text-xs text-fg-subtle">{user.full_name ?? '-'}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{user.role}</td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{user.subscription_status ?? '-'}</td>
                    <td className="px-4 py-3 text-sm text-fg-muted">{formatDate(user.subscription_ends_at)}</td>
                    <td className="max-w-[240px] truncate px-4 py-3 text-xs text-fg-subtle">{user.stripe_customer_id ?? '-'}</td>
                    <td className="max-w-[240px] truncate px-4 py-3 text-xs text-fg-subtle">{user.stripe_subscription_id ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>{total.toLocaleString()} users</span>
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
