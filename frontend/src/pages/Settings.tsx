import { useEffect, useState } from 'react'
import { ArrowPathIcon, BellAlertIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { cvApi } from '../services/api'
import { getPreferences, updatePreferences, type AlertPreferences } from '../services/alertsApi'

export default function Settings() {
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

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <BellAlertIcon className="h-7 w-7 text-brand-500" />
          Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500">Manage job match alert preferences.</p>
      </div>

      {!hasDefaultCv && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Set a default CV to receive useful high-match alerts.
        </div>
      )}

      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        {loading || !preferences ? (
          <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
        ) : (
          <div className="space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Job match alerts</h2>
              <p className="mt-1 text-xs text-gray-500">
                Receive a digest when newly scored jobs meet your match threshold.
              </p>
            </div>

            <label className="flex items-center justify-between gap-4 rounded-xl border border-gray-200 px-4 py-3">
              <span>
                <span className="block text-sm font-medium text-gray-900">Enable alerts</span>
                <span className="block text-xs text-gray-500">Email notifications for high-match jobs.</span>
              </span>
              <input
                type="checkbox"
                checked={preferences.enabled}
                onChange={(event) =>
                  setPreferences({ ...preferences, enabled: event.target.checked })
                }
                className="h-5 w-5 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-600">
                  Score threshold
                </span>
                <input
                  type="number"
                  min={60}
                  max={95}
                  value={preferences.score_threshold}
                  onChange={(event) =>
                    setPreferences({
                      ...preferences,
                      score_threshold: Number(event.target.value),
                    })
                  }
                  className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </label>

              <label className="space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-600">
                  Frequency
                </span>
                <select
                  value={preferences.frequency}
                  onChange={(event) =>
                    setPreferences({
                      ...preferences,
                      frequency: event.target.value as AlertPreferences['frequency'],
                    })
                  }
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
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
      </div>
    </div>
  )
}
