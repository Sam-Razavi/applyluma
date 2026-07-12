import { useEffect, useState } from 'react'
import ErrorBanner from '../../components/ui/ErrorBanner'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminDatabaseStatsResponse } from '../../services/adminApi'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`
}

function formatGrowth(value: number | null): string {
  if (value === null) return '—'
  return value > 0 ? `+${value.toLocaleString()}` : value.toLocaleString()
}

export default function AdminDatabase() {
  const [stats, setStats] = useState<AdminDatabaseStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Database — ApplyLuma'
    adminApi
      .getDatabaseStats()
      .then(setStats)
      .catch(() => setError('Failed to load database stats'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Database</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Table sizes and growth. Row counts are approximate (Postgres
            planner estimates), not exact.
          </p>
        </div>

        {error && <ErrorBanner message={error} />}

        {loading ? (
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-track" />
            ))}
          </div>
        ) : stats && (
          <>
            <section className="rounded-2xl border border-line bg-surface p-5">
              <p className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
                Total Database Size
              </p>
              <p className="mt-1 text-2xl font-bold text-fg">{formatBytes(stats.database_size_bytes)}</p>
            </section>

            <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
              <table className="min-w-full divide-y divide-line">
                <thead className="bg-surface">
                  <tr>
                    {['Table', '~ Rows', 'Size', '+7 days', '+30 days'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-fg-subtle"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {stats.tables.map((table) => (
                    <tr key={table.table_name} className="hover:bg-surface-strong transition-colors">
                      <td className="px-4 py-3 text-sm font-medium text-fg">{table.table_name}</td>
                      <td className="px-4 py-3 text-sm text-fg-muted">
                        {table.approx_row_count.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-fg-muted">{formatBytes(table.total_bytes)}</td>
                      <td className="px-4 py-3 text-xs text-fg-subtle">{formatGrowth(table.rows_7d)}</td>
                      <td className="px-4 py-3 text-xs text-fg-subtle">{formatGrowth(table.rows_30d)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </FadeIn>
  )
}
