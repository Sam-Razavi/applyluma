import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { FadeIn } from '../../components/ui/FadeIn'
import {
  adminApi,
  type AdminFunnelStats,
  type AdminUserProfile,
  type AdminUserRow,
  type UserSignupsDailyPoint,
} from '../../services/adminApi'
import UserDrawer from './UserDrawer'

const ROLE_BADGE: Record<AdminUserRow['role'], string> = {
  user: 'bg-chip-accent text-accent-text',
  premium: 'bg-chip-accent text-accent-text',
  admin: 'bg-chip-danger text-chip-danger-fg',
}

interface NotifyModal {
  user: AdminUserRow
  title: string
  body: string
  submitting: boolean
}

function FunnelStat({ label, value, of }: { label: string; value: number; of?: number }) {
  const pct = of && of > 0 ? `${((value / of) * 100).toFixed(0)}%` : undefined
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <p className="text-xs font-medium text-fg-subtle">{label}</p>
      <p className="mt-1 text-2xl font-bold text-fg">{value.toLocaleString()}</p>
      {pct && <p className="mt-0.5 text-xs text-fg-subtle">{pct} of registered</p>}
    </div>
  )
}

export default function AdminUsers() {
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [notifyModal, setNotifyModal] = useState<NotifyModal | null>(null)
  const [profile, setProfile] = useState<AdminUserProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [funnel, setFunnel] = useState<AdminFunnelStats | null>(null)
  const [signupsDaily, setSignupsDaily] = useState<UserSignupsDailyPoint[]>([])
  const [growthLoading, setGrowthLoading] = useState(true)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const size = 25
  const totalPages = Math.max(1, Math.ceil(total / size))

  useEffect(() => {
    document.title = 'User Management — ApplyLuma'
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [search])

  useEffect(() => {
    setPage(1)
  }, [roleFilter])

  const fetchUsers = useCallback(() => {
    setLoading(true)
    adminApi
      .listUsers({
        search: debouncedSearch || undefined,
        role: roleFilter || undefined,
        page,
        size,
      })
      .then((data) => {
        setUsers(data.items)
        setTotal(data.total)
      })
      .catch(() => toast.error('Failed to load users'))
      .finally(() => setLoading(false))
  }, [debouncedSearch, roleFilter, page])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  useEffect(() => {
    setGrowthLoading(true)
    Promise.all([adminApi.getUserSignupsDaily(30), adminApi.getUserFunnel()])
      .then(([daily, f]) => {
        setSignupsDaily(daily)
        setFunnel(f)
      })
      .catch(() => toast.error('Failed to load signup analytics'))
      .finally(() => setGrowthLoading(false))
  }, [])

  async function handleRoleChange(userId: string, role: AdminUserRow['role']) {
    try {
      const updated = await adminApi.updateRole(userId, role)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)))
      toast.success('Role updated')
    } catch {
      toast.error('Failed to update role')
    }
  }

  async function handleActiveToggle(userId: string, is_active: boolean) {
    try {
      const updated = await adminApi.updateActive(userId, is_active)
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)))
      toast.success(is_active ? 'Account enabled' : 'Account disabled')
    } catch {
      toast.error('Failed to update account')
    }
  }

  async function handleNotifySubmit() {
    if (!notifyModal) return
    setNotifyModal((m) => m && { ...m, submitting: true })
    try {
      await adminApi.sendNotification(notifyModal.user.id, notifyModal.title, notifyModal.body)
      toast.success(`Notification sent to ${notifyModal.user.email}`)
      setNotifyModal(null)
    } catch {
      toast.error('Failed to send notification')
      setNotifyModal((m) => m && { ...m, submitting: false })
    }
  }

  async function openProfile(userId: string) {
    setProfileLoading(true)
    try {
      const data = await adminApi.getUserProfile(userId)
      setProfile(data)
    } catch {
      toast.error('Failed to load user profile')
    } finally {
      setProfileLoading(false)
    }
  }

  function closeProfile() {
    setProfile(null)
    setProfileLoading(false)
  }

  function handleUserChanged() {
    fetchUsers()
    if (profile) {
      adminApi
        .getUserProfile(profile.id)
        .then(setProfile)
        .catch(() => undefined)
    }
  }

  const start = (page - 1) * size + 1
  const end = Math.min(page * size, total)

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg ">User Management</h1>
          <p className="mt-1 text-sm text-fg-subtle ">
            {total > 0 ? `${total.toLocaleString()} users` : 'Loading…'}
          </p>
        </div>

        {/* Growth & tailor-usage funnel */}
        <section className="space-y-4">
          {growthLoading && !funnel ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-2xl bg-track" />
              ))}
            </div>
          ) : funnel ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <FunnelStat label="Registered" value={funnel.registered} />
              <FunnelStat label="Verified" value={funnel.verified} of={funnel.registered} />
              <FunnelStat label="Uploaded a CV" value={funnel.has_cv} of={funnel.registered} />
              <FunnelStat
                label="Attempted tailor"
                value={funnel.attempted_tailor}
                of={funnel.registered}
              />
              <FunnelStat
                label="Completed tailor"
                value={funnel.completed_tailor}
                of={funnel.registered}
              />
            </div>
          ) : null}

          <div className="rounded-2xl border border-line bg-surface p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
              Daily signups (30 days)
            </h2>
            <div className="mt-4">
              {signupsDaily.length === 0 ? (
                <p className="py-10 text-center text-sm text-fg-subtle">
                  {growthLoading ? 'Loading…' : 'No signups recorded yet.'}
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={signupsDaily} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--track)" />
                    <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 12 }} tickLine={false} />
                    <YAxis tick={{ fill: 'var(--text-3)', fontSize: 12 }} tickLine={false} allowDecimals={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" name="Signups" stroke="#6366f1" strokeWidth={2} dot={false} />
                    <Line
                      type="monotone"
                      dataKey="verified_count"
                      name="Verified same day"
                      stroke="#34c38f"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </section>

        {/* Filters */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="search"
            placeholder="Search by email or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 rounded-lg border border-line-strong px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-line-strong px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
          >
            <option value="">All roles</option>
            <option value="user">User</option>
            <option value="premium">Premium</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-2xl border border-line bg-surface ">
          {loading ? (
            <div className="space-y-3 p-5">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-track " />
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="py-12 text-center text-sm text-fg-subtle">No users found.</div>
          ) : (
            <table className="min-w-full divide-y divide-line ">
              <thead className="bg-surface ">
                <tr>
                  {['Email', 'Name', 'Role', 'Status', 'Active', 'Joined', 'Last login', 'Actions'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle "
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line ">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-surface-strong transition-colors">
                    <td className="px-4 py-3 text-sm text-fg max-w-[200px] truncate">
                      {u.email}
                    </td>
                    <td className="px-4 py-3 text-sm text-fg-muted max-w-[140px] truncate">
                      {u.full_name ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value as AdminUserRow['role'])}
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 ${ROLE_BADGE[u.role]}`}
                      >
                        <option value="user">user</option>
                        <option value="premium">premium</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle ">
                      {u.subscription_status ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleActiveToggle(u.id, !u.is_active)}
                        className={`inline-flex h-5 w-9 flex-shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                          u.is_active ? 'bg-green-500' : 'bg-track '
                        }`}
                        role="switch"
                        aria-checked={u.is_active}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
                            u.is_active ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">
                      {new Date(u.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-4 py-3 text-xs text-fg-subtle">
                      {u.last_login_at
                        ? new Date(u.last_login_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-3">
                        <button
                          onClick={() => openProfile(u.id)}
                          className="text-xs font-medium text-accent-text hover:text-primary-800 transition-colors"
                        >
                          View
                        </button>
                        <button
                          onClick={() =>
                            setNotifyModal({ user: u, title: '', body: '', submitting: false })
                          }
                          className="text-xs font-medium text-accent-text hover:text-primary-800 transition-colors"
                        >
                          Notify
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {total > size && (
          <div className="flex items-center justify-between text-sm text-fg-subtle">
            <span>
              Showing {start}–{end} of {total.toLocaleString()} users
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium hover:bg-surface-strong disabled:cursor-not-allowed disabled:opacity-40 "
              >
                Previous
              </button>
              <span className="flex items-center px-2 text-xs">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium hover:bg-surface-strong disabled:cursor-not-allowed disabled:opacity-40 "
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Notify modal (portaled: page wrapper transform would break
          position:fixed) */}
      {notifyModal && createPortal(
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setNotifyModal(null)
          }}
        >
          <div className="w-full max-w-md rounded-2xl bg-surface p-6 shadow-xl ">
            <h3 className="mb-1 text-base font-semibold text-fg ">
              Send Notification
            </h3>
            <p className="mb-4 text-xs text-fg-subtle truncate">To: {notifyModal.user.email}</p>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Title"
                value={notifyModal.title}
                onChange={(e) => setNotifyModal((m) => m && { ...m, title: e.target.value })}
                className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
              />
              <textarea
                placeholder="Message body"
                rows={4}
                value={notifyModal.body}
                onChange={(e) => setNotifyModal((m) => m && { ...m, body: e.target.value })}
                className="w-full resize-none rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setNotifyModal(null)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-strong "
              >
                Cancel
              </button>
              <button
                onClick={handleNotifySubmit}
                disabled={!notifyModal.title.trim() || !notifyModal.body.trim() || notifyModal.submitting}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {notifyModal.submitting ? 'Sending…' : 'Send'}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}

      {(profile || profileLoading) && (
        <UserDrawer
          profile={profile}
          loading={profileLoading}
          onClose={closeProfile}
          onUserChanged={handleUserChanged}
        />
      )}
    </FadeIn>
  )
}
