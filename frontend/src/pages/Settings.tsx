import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowPathIcon,
  BellAlertIcon,
  EyeIcon,
  EyeSlashIcon,
  KeyIcon,
  MoonIcon,
  SunIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { type AxiosError } from 'axios'
import toast from 'react-hot-toast'
import { cvApi } from '../services/api'
import { getPreferences, updatePreferences, type AlertPreferences } from '../services/alertsApi'
import { authApi } from '../services/authApi'
import { useAuthStore } from '../stores'
import { useThemeStore } from '../stores/theme'

export default function Settings() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const { dark, toggle: toggleDark } = useThemeStore()

  // ── Alert preferences ────────────────────────────────────────────────────
  const [preferences, setPreferences] = useState<AlertPreferences | null>(null)
  const [hasDefaultCv, setHasDefaultCv] = useState(true)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    document.title = 'Settings | ApplyLuma'
    Promise.all([getPreferences(), cvApi.list()])
      .then(([prefs, cvs]) => {
        setPreferences(prefs)
        setHasDefaultCv(cvs.some((cv) => cv.is_default))
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
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900 dark:text-white">
          Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account and preferences.
        </p>
      </div>

      {!hasDefaultCv && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Set a default CV to receive useful high-match alerts.
        </div>
      )}

      {/* ── Appearance ─────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex items-center gap-2">
          {dark ? (
            <MoonIcon className="h-5 w-5 text-brand-500" />
          ) : (
            <SunIcon className="h-5 w-5 text-brand-500" />
          )}
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Appearance</h2>
        </div>

        <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-600">
          <span>
            <span className="block text-sm font-medium text-gray-900 dark:text-white">
              Dark mode
            </span>
            <span className="block text-xs text-gray-500 dark:text-gray-400">
              Switch between light and dark theme.
            </span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={dark}
            onClick={toggleDark}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
              dark ? 'bg-brand-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                dark ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </label>
      </section>

      {/* ── Job match alerts ───────────────────────────────────────────── */}
      <section className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex items-center gap-2">
          <BellAlertIcon className="h-5 w-5 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Job match alerts</h2>
        </div>

        {loading || !preferences ? (
          <div className="h-40 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-700" />
        ) : (
          <div className="space-y-5">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Receive a digest when newly scored jobs meet your match threshold.
            </p>

            <label className="flex items-center justify-between gap-4 rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-600">
              <span>
                <span className="block text-sm font-medium text-gray-900 dark:text-white">
                  Enable alerts
                </span>
                <span className="block text-xs text-gray-500 dark:text-gray-400">
                  Email notifications for high-match jobs.
                </span>
              </span>
              <input
                type="checkbox"
                checked={preferences.enabled}
                onChange={(e) => setPreferences({ ...preferences, enabled: e.target.checked })}
                className="h-5 w-5 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400">
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
                  className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
              </label>

              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400">
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
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
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
      <section className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex items-center gap-2">
          <KeyIcon className="h-5 w-5 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Change password</h2>
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
              <span className="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400">
                {label}
              </span>
              <div className="relative">
                <input
                  type={show ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-200 px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
                <button
                  type="button"
                  onClick={onToggle}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
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
      <section className="rounded-2xl border border-red-200 bg-white p-6 dark:border-red-900/40 dark:bg-gray-800">
        <div className="mb-4 flex items-center gap-2">
          <TrashIcon className="h-5 w-5 text-red-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Delete account</h2>
        </div>
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Permanently deletes your account and all associated data. This cannot be undone.
        </p>
        <button
          type="button"
          onClick={() => setDeleteOpen(true)}
          className="rounded-xl border border-red-300 px-5 py-2.5 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
        >
          Delete my account
        </button>
      </section>

      {/* ── Delete confirmation modal ──────────────────────────────────── */}
      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Delete account?
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              This will permanently delete your account, CVs, applications, and all other data.
              Type <strong className="text-gray-900 dark:text-white">DELETE</strong> to confirm.
            </p>
            <input
              ref={deleteInputRef}
              type="text"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder="DELETE"
              className="mt-4 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteOpen(false)}
                className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
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
