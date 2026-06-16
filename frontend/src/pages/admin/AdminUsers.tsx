import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminUserRow } from '../../services/adminApi'

const ROLE_BADGE: Record<AdminUserRow['role'], string> = {
  user: 'bg-[rgba(8,145,178,0.15)] text-cyan-300',
  premium: 'bg-[rgba(8,145,178,0.15)] text-cyan-300',
  admin: 'bg-[rgba(229,72,77,0.12)] text-red-300',
}

interface NotifyModal {
  user: AdminUserRow
  title: string
  body: string
  submitting: boolean
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

  const start = (page - 1) * size + 1
  const end = Math.min(page * size, total)

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white/90 ">User Management</h1>
          <p className="mt-1 text-sm text-white/30 ">
            {total > 0 ? `${total.toLocaleString()} users` : 'Loading…'}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="search"
            placeholder="Search by email or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 rounded-lg border border-white/15 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-white/15 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
          >
            <option value="">All roles</option>
            <option value="user">User</option>
            <option value="premium">Premium</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.04] ">
          {loading ? (
            <div className="space-y-3 p-5">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-white/[0.04] " />
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="py-12 text-center text-sm text-white/30">No users found.</div>
          ) : (
            <table className="min-w-full divide-y divide-white/10 ">
              <thead className="bg-white/[0.03] ">
                <tr>
                  {['Email', 'Name', 'Role', 'Status', 'Active', 'Joined', 'Actions'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-white/30 "
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 ">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-white/[0.04] transition-colors">
                    <td className="px-4 py-3 text-sm text-white/90 max-w-[200px] truncate">
                      {u.email}
                    </td>
                    <td className="px-4 py-3 text-sm text-white/55 max-w-[140px] truncate">
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
                    <td className="px-4 py-3 text-xs text-white/30 ">
                      {u.subscription_status ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleActiveToggle(u.id, !u.is_active)}
                        className={`inline-flex h-5 w-9 flex-shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                          u.is_active ? 'bg-green-500' : 'bg-white/20 '
                        }`}
                        role="switch"
                        aria-checked={u.is_active}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white/[0.04] shadow ring-0 transition-transform ${
                            u.is_active ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-white/30">
                      {new Date(u.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() =>
                          setNotifyModal({ user: u, title: '', body: '', submitting: false })
                        }
                        className="text-xs font-medium text-primary-400 hover:text-primary-800 transition-colors"
                      >
                        Notify
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {total > size && (
          <div className="flex items-center justify-between text-sm text-white/30">
            <span>
              Showing {start}–{end} of {total.toLocaleString()} users
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium hover:bg-white/[0.04] disabled:cursor-not-allowed disabled:opacity-40 "
              >
                Previous
              </button>
              <span className="flex items-center px-2 text-xs">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium hover:bg-white/[0.04] disabled:cursor-not-allowed disabled:opacity-40 "
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Notify modal */}
      {notifyModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setNotifyModal(null)
          }}
        >
          <div className="w-full max-w-md rounded-2xl bg-white/[0.04] p-6 shadow-xl ">
            <h3 className="mb-1 text-base font-semibold text-white/90 ">
              Send Notification
            </h3>
            <p className="mb-4 text-xs text-white/30 truncate">To: {notifyModal.user.email}</p>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Title"
                value={notifyModal.title}
                onChange={(e) => setNotifyModal((m) => m && { ...m, title: e.target.value })}
                className="w-full rounded-lg border border-white/15 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
              />
              <textarea
                placeholder="Message body"
                rows={4}
                value={notifyModal.body}
                onChange={(e) => setNotifyModal((m) => m && { ...m, body: e.target.value })}
                className="w-full resize-none rounded-lg border border-white/15 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 "
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setNotifyModal(null)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-white/55 hover:bg-white/[0.06] "
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
        </div>
      )}
    </FadeIn>
  )
}
