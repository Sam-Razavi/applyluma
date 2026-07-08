import { useEffect, useState } from 'react'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type SystemHealthResponse } from '../../services/adminApi'

function badgeClass(status: string) {
  if (status === 'ok') return 'bg-chip-success text-chip-success-fg'
  if (status === 'unhealthy') return 'bg-chip-danger text-chip-danger-fg'
  return 'bg-chip-accent text-accent-text'
}

export default function AdminSystem() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'System Health - ApplyLuma'
    adminApi
      .getSystemHealth()
      .then(setHealth)
      .catch(() => setError('Failed to load system health'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">System Health</h1>
          <p className="mt-1 text-sm text-fg-subtle">Runtime checks for core infrastructure and external configuration.</p>
        </div>

        {error && <div className="rounded-xl border border-chip-danger bg-chip-danger p-4 text-sm text-chip-danger-fg">{error}</div>}

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 animate-pulse rounded-2xl border border-line bg-surface" />
            ))}
          </div>
        ) : health && (
          <>
            <section className="rounded-2xl border border-line bg-surface p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-fg-muted">Overall</p>
                  <p className="mt-1 text-sm text-fg-subtle">Version {health.version}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-sm font-semibold ${badgeClass(health.status)}`}>
                  {health.status}
                </span>
              </div>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(health.checks).map(([name, check]) => (
                <section key={name} className="rounded-2xl border border-line bg-surface p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-base font-semibold capitalize text-fg">{name}</h2>
                      <p className="mt-1 text-sm text-fg-subtle">{check.detail}</p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass(check.status)}`}>
                      {check.status}
                    </span>
                  </div>
                  {Object.entries(check)
                    .filter(([key]) => !['status', 'detail'].includes(key))
                    .map(([key, value]) => (
                      <p key={key} className="mt-3 break-all text-xs text-fg-subtle">
                        <span className="font-semibold">{key}:</span> {JSON.stringify(value)}
                      </p>
                    ))}
                </section>
              ))}
            </div>
          </>
        )}
      </div>
    </FadeIn>
  )
}
