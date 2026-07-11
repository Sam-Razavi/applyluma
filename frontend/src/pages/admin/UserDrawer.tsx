import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import toast from 'react-hot-toast'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import {
  adminApi,
  type AdminActivityEvent,
  type AdminUserProfile,
} from '../../services/adminApi'

interface Props {
  profile: AdminUserProfile | null
  loading: boolean
  onClose: () => void
  onUserChanged: () => void
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function formatUsd(usd: number): string {
  return `$${usd.toFixed(2)}`
}

const ACTIVITY_LABELS: Record<string, string> = {
  cv_uploaded: 'CV uploaded',
  cv_tailored: 'CV tailored',
  application_created: 'Application created',
  application_event: 'Application updated',
  tailor_job: 'AI tailor run',
  cover_letter: 'Cover letter',
  saved_job: 'Job saved',
  job_description: 'Job description added',
  contact_submission: 'Contact/feedback submitted',
}

export default function UserDrawer({ profile, loading, onClose, onUserChanged }: Props) {
  const [events, setEvents] = useState<AdminActivityEvent[]>([])
  const [eventsTotal, setEventsTotal] = useState(0)
  const [eventsPage, setEventsPage] = useState(1)
  const [eventsLoading, setEventsLoading] = useState(false)

  const [limitInput, setLimitInput] = useState('')
  const [savingLimit, setSavingLimit] = useState(false)

  const [sendingReset, setSendingReset] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    setEvents([])
    setEventsTotal(0)
    setEventsPage(1)
    setLimitInput(
      profile?.daily_tailor_limit_override !== null && profile?.daily_tailor_limit_override !== undefined
        ? String(profile.daily_tailor_limit_override)
        : '',
    )
    if (profile) {
      loadActivity(profile.id, 1, true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.id])

  function loadActivity(userId: string, page: number, replace: boolean) {
    setEventsLoading(true)
    adminApi
      .getUserActivity(userId, page)
      .then((data) => {
        setEvents((prev) => (replace ? data.items : [...prev, ...data.items]))
        setEventsTotal(data.total)
        setEventsPage(page)
      })
      .catch(() => toast.error('Failed to load activity timeline'))
      .finally(() => setEventsLoading(false))
  }

  async function handleSendPasswordReset() {
    if (!profile) return
    setSendingReset(true)
    try {
      await adminApi.sendPasswordReset(profile.id)
      toast.success('Password reset email sent')
    } catch {
      toast.error('Failed to send password reset email')
    } finally {
      setSendingReset(false)
    }
  }

  async function handleVerify() {
    if (!profile) return
    setVerifying(true)
    try {
      await adminApi.verifyUser(profile.id)
      toast.success('User marked as verified')
      onUserChanged()
    } catch {
      toast.error('Failed to verify user')
    } finally {
      setVerifying(false)
    }
  }

  async function handleSaveLimit() {
    if (!profile) return
    const trimmed = limitInput.trim()
    const value = trimmed === '' ? null : Number(trimmed)
    if (value !== null && (!Number.isInteger(value) || value < 0)) {
      toast.error('Limit must be a non-negative whole number')
      return
    }
    setSavingLimit(true)
    try {
      await adminApi.updateLimits(profile.id, value)
      toast.success('Tailor limit updated')
      onUserChanged()
    } catch {
      toast.error('Failed to update limit')
    } finally {
      setSavingLimit(false)
    }
  }

  async function handleClearLimit() {
    if (!profile) return
    setLimitInput('')
    setSavingLimit(true)
    try {
      await adminApi.updateLimits(profile.id, null)
      toast.success('Tailor limit reset to role default')
      onUserChanged()
    } catch {
      toast.error('Failed to reset limit')
    } finally {
      setSavingLimit(false)
    }
  }

  async function handleDelete() {
    if (!profile) return
    setDeleting(true)
    try {
      await adminApi.deleteUser(profile.id)
      toast.success(`Deleted ${profile.email}`)
      setConfirmDelete(false)
      onClose()
      onUserChanged()
    } catch {
      toast.error('Failed to delete user')
    } finally {
      setDeleting(false)
    }
  }

  if (!profile && !loading) return null

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-surface p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-fg">User Profile</h3>
            <p className="mt-1 text-sm text-fg-subtle">
              {profile?.email ?? 'Loading user details...'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-fg-muted hover:bg-surface-strong"
          >
            Close
          </button>
        </div>

        {loading ? (
          <div className="mt-6 space-y-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-track" />
            ))}
          </div>
        ) : profile && (
          <div className="mt-6 space-y-6">
            <section className="grid gap-3 sm:grid-cols-2">
              {[
                ['Name', profile.full_name ?? '-'],
                ['Role', profile.role],
                ['Active', profile.is_active ? 'yes' : 'no'],
                ['Verified', profile.is_verified ? 'yes' : 'no'],
                ['Auth provider', profile.auth_provider ?? '-'],
                ['Subscription', profile.subscription_status ?? '-'],
                ['Joined', new Date(profile.created_at).toLocaleString()],
                ['Updated', new Date(profile.updated_at).toLocaleString()],
                ['Last login', formatDate(profile.last_login_at)],
                ['Login count', profile.login_count.toLocaleString()],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-line bg-surface-strong p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">{label}</p>
                  <p className="mt-1 break-all text-sm text-fg">{value}</p>
                </div>
              ))}
            </section>

            <section>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">Activity</h4>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {Object.entries(profile.activity).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-line bg-surface-strong p-3">
                    <p className="text-xs capitalize text-fg-subtle">{key.replace(/_/g, ' ')}</p>
                    <p className="mt-1 text-2xl font-bold text-fg">{value.toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">AI Spend</h4>
              <div className="mt-3 grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-line bg-surface-strong p-3">
                  <p className="text-xs text-fg-subtle">Last 30 days</p>
                  <p className="mt-1 text-lg font-bold text-fg">
                    {formatUsd(profile.ai_costs.last_30_days_usd)}
                  </p>
                </div>
                <div className="rounded-xl border border-line bg-surface-strong p-3">
                  <p className="text-xs text-fg-subtle">All time</p>
                  <p className="mt-1 text-lg font-bold text-fg">
                    {formatUsd(profile.ai_costs.all_time_usd)}
                  </p>
                </div>
                <div className="rounded-xl border border-line bg-surface-strong p-3">
                  <p className="text-xs text-fg-subtle">AI calls</p>
                  <p className="mt-1 text-lg font-bold text-fg">
                    {profile.ai_costs.all_time_calls.toLocaleString()}
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
                Daily Tailor Limit
              </h4>
              <p className="mt-1 text-xs text-fg-subtle">
                Leave empty to use the role default. Set to 0 to block tailoring entirely.
              </p>
              <div className="mt-3 flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  value={limitInput}
                  onChange={(e) => setLimitInput(e.target.value)}
                  placeholder="Role default"
                  className="w-32 rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
                <button
                  onClick={handleSaveLimit}
                  disabled={savingLimit}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40"
                >
                  Save
                </button>
                <button
                  onClick={handleClearLimit}
                  disabled={savingLimit || profile.daily_tailor_limit_override === null}
                  className="rounded-lg border border-line-strong px-4 py-2 text-sm font-medium hover:bg-surface-strong disabled:opacity-40"
                >
                  Clear
                </button>
              </div>
            </section>

            <section>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">Billing IDs</h4>
              <div className="mt-3 space-y-2 text-xs text-fg-subtle">
                <p className="break-all"><span className="font-semibold">Customer:</span> {profile.stripe_customer_id ?? '-'}</p>
                <p className="break-all"><span className="font-semibold">Subscription:</span> {profile.stripe_subscription_id ?? '-'}</p>
                <p><span className="font-semibold">Ends:</span> {profile.subscription_ends_at ? new Date(profile.subscription_ends_at).toLocaleString() : '-'}</p>
              </div>
            </section>

            <section>
              <h4 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">Timeline</h4>
              {eventsLoading && events.length === 0 ? (
                <div className="mt-3 space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-8 animate-pulse rounded-lg bg-track" />
                  ))}
                </div>
              ) : events.length === 0 ? (
                <p className="mt-3 text-sm text-fg-subtle">No activity recorded yet.</p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {events.map((event, idx) => (
                    <li key={idx} className="flex gap-3">
                      <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-primary-500" />
                      <div className="min-w-0">
                        <p className="text-sm text-fg">
                          <span className="font-medium">{ACTIVITY_LABELS[event.type] ?? event.type}</span>
                          {event.status && (
                            <span className="ml-2 text-xs text-fg-subtle">({event.status})</span>
                          )}
                        </p>
                        <p className="truncate text-xs text-fg-subtle">{event.title}</p>
                        <p className="text-xs text-fg-subtle">{new Date(event.timestamp).toLocaleString()}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {events.length < eventsTotal && (
                <button
                  onClick={() => loadActivity(profile.id, eventsPage + 1, false)}
                  disabled={eventsLoading}
                  className="mt-3 text-xs font-medium text-accent-text hover:text-primary-800 disabled:opacity-40"
                >
                  {eventsLoading ? 'Loading…' : 'Load more'}
                </button>
              )}
            </section>

            <section className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-red-600">Danger Zone</h4>
              <div className="mt-3 flex flex-wrap gap-2">
                {profile.auth_provider !== 'google' && (
                  <button
                    onClick={handleSendPasswordReset}
                    disabled={sendingReset}
                    className="rounded-lg border border-line-strong px-3 py-2 text-xs font-medium hover:bg-surface-strong disabled:opacity-40"
                  >
                    {sendingReset ? 'Sending…' : 'Send password reset'}
                  </button>
                )}
                {!profile.is_verified && (
                  <button
                    onClick={handleVerify}
                    disabled={verifying}
                    className="rounded-lg border border-line-strong px-3 py-2 text-xs font-medium hover:bg-surface-strong disabled:opacity-40"
                  >
                    {verifying ? 'Verifying…' : 'Mark verified'}
                  </button>
                )}
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="rounded-lg bg-red-600 px-3 py-2 text-xs font-medium text-white hover:bg-red-700"
                >
                  Delete user
                </button>
              </div>
            </section>
          </div>
        )}
      </aside>

      {profile && (
        <ConfirmDialog
          open={confirmDelete}
          title="Delete this user?"
          message="This permanently deletes the user and all their CVs, applications, saved jobs, and AI job history. This cannot be undone."
          confirmLabel="Delete user"
          requireText={profile.email}
          loading={deleting}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={handleDelete}
        />
      )}
    </div>,
    document.body,
  )
}
