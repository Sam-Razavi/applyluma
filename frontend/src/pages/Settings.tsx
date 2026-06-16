import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowPathIcon,
  BellAlertIcon,
  CreditCardIcon,
  EyeIcon,
  EyeSlashIcon,
  KeyIcon,
  MoonIcon,
  SparklesIcon,
  SunIcon,
  TrashIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline'
import { type AxiosError } from 'axios'
import toast from 'react-hot-toast'
import { cvApi } from '../services/api'
import { getPreferences, updatePreferences, type AlertPreferences } from '../services/alertsApi'
import { authApi } from '../services/authApi'
import { tailorApi } from '../services/tailorApi'
import { useAuthStore } from '../stores'
import { useThemeStore } from '../stores/theme'
import type { TailorUsage } from '../types/tailor'

export default function Settings() {
  const navigate = useNavigate()
  const { user, setUser, logout } = useAuthStore()
  const { dark, toggle: toggleDark } = useThemeStore()

  // ── Profile ───────────────────────────────────────────────────────────────
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [savingProfile, setSavingProfile] = useState(false)

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault()
    setSavingProfile(true)
    try {
      const updated = await authApi.updateProfile(fullName.trim())
      setUser(updated)
      toast.success('Profile updated')
    } catch {
      toast.error('Failed to update profile')
    } finally {
      setSavingProfile(false)
    }
  }

  // ── Account / usage ──────────────────────────────────────────────────────
  const [usage, setUsage] = useState<TailorUsage | null>(null)

  // ── Alert preferences ────────────────────────────────────────────────────
  const [preferences, setPreferences] = useState<AlertPreferences | null>(null)
  const [hasDefaultCv, setHasDefaultCv] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    document.title = 'Settings | ApplyLuma'
    Promise.all([getPreferences(), cvApi.list(), tailorApi.getUsage()])
      .then(([prefs, cvs, u]) => {
        setPreferences(prefs)
        setHasDefaultCv(cvs.some((cv) => cv.is_default))
        setUsage(u)
      })
      .catch(() => toast.error('Failed to load settings'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    if (!preferences) return
    setSaving(true)
    try {
      const updated = await updatePreferences({
        enabled: preferences.enabled,
        score_threshold: preferences.score_threshold,
        frequency: preferences.frequency,
      })
      setPreferences(updated)
      toast.success('Alert settings saved')
    } catch {
      toast.error('Failed to save alert settings')
    } finally {
      setSaving(false)
    }
  }

  // ── Change password ───────────────────────────────────────────────────────
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [changingPassword, setChangingPassword] = useState(false)

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters')
      return
    }
    setChangingPassword(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      toast.success('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      const detail = (err as AxiosError<{ detail: string }>)?.response?.data?.detail
      toast.error(detail || 'Failed to change password')
    } finally {
      setChangingPassword(false)
    }
  }

  // ── Delete account ────────────────────────────────────────────────────────
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleting, setDeleting] = useState(false)
  const deleteInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (deleteOpen) setTimeout(() => deleteInputRef.current?.focus(), 50)
    else setDeleteConfirm('')
  }, [deleteOpen])

  async function handleDeleteAccount() {
    if (deleteConfirm !== 'DELETE') return
    setDeleting(true)
    try {
      await authApi.deleteAccount()
      logout()
      navigate('/login')
    } catch {
      toast.error('Failed to delete account')
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-white/90 ">
          Settings
        </h1>
        <p className="mt-1 text-sm text-white/30 ">
          Manage your account and preferences.
        </p>
      </div>

      {/* ── Profile ──────────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 ">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-white/90 ">
          <UserCircleIcon className="h-4 w-4 text-white/30" />
          Profile
        </h2>
        <form onSubmit={(e) => void handleSaveProfile(e)} className="mt-4 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/55 ">
              Display name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
              className="input w-full"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/55 ">
              Email
            </label>
            <input
              type="email"
              value={user?.email ?? ''}
              disabled
              className="input w-full cursor-not-allowed opacity-60"
            />
          </div>
          <button
            type="submit"
            disabled={savingProfile || fullName.trim() === (user?.full_name ?? '')}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {savingProfile && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            Save profile
          </button>
        </form>
      </section>

      {!hasDefaultCv && (
        <div className="rounded-xl border border-[rgba(245,158,11,0.20)] bg-[rgba(245,158,11,0.14)] px-4 py-3 text-sm text-amber-300">
          Set a default CV to receive useful high-match alerts.
        </div>
      )}

      {/* ── Account ──────────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 ">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-white/90 ">
          <CreditCardIcon className="h-4 w-4 text-white/30" />
          Account
        </h2>

        <div className="mt-4 space-y-5">
          {/* Plan badge */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-white/30 ">Current plan</p>
              <div className="mt-1 flex items-center gap-2">
                {user?.role === 'premium' || user?.role === 'admin' ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-violet-500 to-indigo-600 px-3 py-0.5 text-xs font-bold text-white">
                    <SparklesIcon className="h-3 w-3" />
                    {user.role === 'admin' ? 'Admin' : 'Premium'}
                  </span>
                ) : (
                  <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-0.5 text-xs font-semibold text-white/55 ">
                    Free
                  </span>
                )}
              </div>
            </div>
            {user?.role === 'user' && (
              <Link
                to="/plans"
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:opacity-90"
              >
                <SparklesIcon className="h-3.5 w-3.5" />
                Upgrade
              </Link>
            )}
          </div>

          {/* AI Tailor usage */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <p className="text-xs font-medium text-white/30 ">
                AI Tailor usage today
              </p>
              {loading || !usage ? (
                <span className="h-4 w-16 animate-pulse rounded bg-white/[0.04] " />
              ) : usage.daily_limit === null ? (
                <span className="text-xs font-semibold text-emerald-300">Unlimited</span>
              ) : (
                <span className={`text-xs font-semibold ${usage.used_today >= usage.daily_limit ? 'text-red-300' : 'text-white/55 '}`}>
                  {usage.used_today} / {usage.daily_limit} used
                </span>
              )}
            </div>
            {!loading && usage && usage.daily_limit !== null && (
              <>
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.04] ">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      usage.used_today >= usage.daily_limit
                        ? 'bg-red-500'
                        : usage.used_today / usage.daily_limit >= 0.75
                          ? 'bg-amber-400'
                          : 'bg-gradient-to-r from-violet-500 to-indigo-500'
                    }`}
                    style={{ width: `${Math.min((usage.used_today / usage.daily_limit) * 100, 100)}%` }}
                  />
                </div>
                {usage.used_today >= usage.daily_limit && user?.role === 'user' && (
                  <p className="mt-1.5 text-xs text-red-300">
                    Limit reached — resets at midnight.{' '}
                    <Link to="/plans" className="font-semibold underline underline-offset-2">
                      Upgrade for 10/day
                    </Link>
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── Appearance ─────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 ">
        <div className="mb-4 flex items-center gap-2">
          {dark ? (
            <MoonIcon className="h-5 w-5 text-primary-400" />
          ) : (
            <SunIcon className="h-5 w-5 text-primary-400" />
          )}
          <h2 className="text-sm font-semibold text-white/90 ">Appearance</h2>
        </div>

        <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-white/10 px-4 py-3 ">
          <span>
            <span className="block text-sm font-medium text-white/90 ">
              Dark mode
            </span>
            <span className="block text-xs text-white/30 ">
              Switch between light and dark theme.
            </span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={dark}
            onClick={toggleDark}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
              dark ? 'bg-brand-600' : 'bg-white/[0.06]'
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white/[0.04] shadow ring-0 transition duration-200 ${
                dark ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </label>
      </section>

      {/* ── Job match alerts ───────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 ">
        <div className="mb-4 flex items-center gap-2">
          <BellAlertIcon className="h-5 w-5 text-primary-400" />
          <h2 className="text-sm font-semibold text-white/90 ">Job match alerts</h2>
        </div>

        {loading || !preferences ? (
          <div className="h-40 animate-pulse rounded-xl bg-white/[0.04] " />
        ) : (
          <div className="space-y-5">
            <p className="text-xs text-white/30 ">
              Receive a digest when newly scored jobs meet your match threshold.
            </p>

            <label className="flex items-center justify-between gap-4 rounded-xl border border-white/10 px-4 py-3 ">
              <span>
                <span className="block text-sm font-medium text-white/90 ">
                  Enable alerts
                </span>
                <span className="block text-xs text-white/30 ">
                  Email notifications for high-match jobs.
                </span>
              </span>
              <input
                type="checkbox"
                checked={preferences.enabled}
                onChange={(e) => setPreferences({ ...preferences, enabled: e.target.checked })}
                className="h-5 w-5 rounded border-white/15 text-primary-400 focus:ring-brand-500"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-white/55 ">
                  Score threshold
                </span>
                <input
                  type="number"
                  min={60}
                  max={95}
                  value={preferences.score_threshold}
                  onChange={(e) =>
                    setPreferences({ ...preferences, score_threshold: Number(e.target.value) })
                  }
                  className="w-full rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 "
                />
              </label>

              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-white/55 ">
                  Frequency
                </span>
                <select
                  value={preferences.frequency}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      frequency: e.target.value as AlertPreferences['frequency'],
                    })
                  }
                  className="w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 "
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </label>
            </div>

            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {saving && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
              Save settings
            </button>
          </div>
        )}
      </section>

      {/* ── Change password ────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 ">
        <div className="mb-4 flex items-center gap-2">
          <KeyIcon className="h-5 w-5 text-primary-400" />
          <h2 className="text-sm font-semibold text-white/90 ">Change password</h2>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-4">
          {[
            {
              label: 'Current password',
              value: currentPassword,
              onChange: setCurrentPassword,
              show: showCurrent,
              onToggle: () => setShowCurrent((v) => !v),
            },
            {
              label: 'New password',
              value: newPassword,
              onChange: setNewPassword,
              show: showNew,
              onToggle: () => setShowNew((v) => !v),
            },
            {
              label: 'Confirm new password',
              value: confirmPassword,
              onChange: setConfirmPassword,
              show: showNew,
              onToggle: () => setShowNew((v) => !v),
            },
          ].map(({ label, value, onChange, show, onToggle }) => (
            <label key={label} className="block space-y-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-white/55 ">
                {label}
              </span>
              <div className="relative">
                <input
                  type={show ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  required
                  className="w-full rounded-lg border border-white/10 px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 "
                />
                <button
                  type="button"
                  onClick={onToggle}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/55"
                  tabIndex={-1}
                >
                  {show ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
            </label>
          ))}

          <button
            type="submit"
            disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
          >
            {changingPassword && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            Update password
          </button>
        </form>
      </section>

      {/* ── Delete account ─────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-[rgba(229,72,77,0.18)] bg-white/[0.04] p-6 ">
        <div className="mb-4 flex items-center gap-2">
          <TrashIcon className="h-5 w-5 text-red-500" />
          <h2 className="text-sm font-semibold text-white/90 ">Delete account</h2>
        </div>
        <p className="mb-4 text-sm text-white/30 ">
          Permanently deletes your account and all associated data. This cannot be undone.
        </p>
        <button
          type="button"
          onClick={() => setDeleteOpen(true)}
          className="rounded-xl border border-[rgba(229,72,77,0.18)] px-5 py-2.5 text-sm font-semibold text-red-300 transition-colors hover:bg-[rgba(229,72,77,0.12)] "
        >
          Delete my account
        </button>
      </section>

      {/* ── Delete confirmation modal ──────────────────────────────────── */}
      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white/[0.04] p-6 shadow-xl ">
            <h3 className="text-lg font-semibold text-white/90 ">
              Delete account?
            </h3>
            <p className="mt-2 text-sm text-white/30 ">
              This will permanently delete your account, CVs, applications, and all other data.
              Type <strong className="text-white/90 ">DELETE</strong> to confirm.
            </p>
            <input
              ref={deleteInputRef}
              type="text"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder="DELETE"
              className="mt-4 w-full rounded-lg border border-white/10 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 "
            />
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteOpen(false)}
                className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-white/55 hover:bg-white/[0.04] "
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={deleteConfirm !== 'DELETE' || deleting}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                {deleting && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
                Delete permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
