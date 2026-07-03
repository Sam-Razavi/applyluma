import type { ApplicationStats as Stats, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import { STATUS_META } from './statusMeta'

interface Props {
  stats: Stats
}

const segmentClasses: Record<ApplicationStatus, string> = {
  wishlist: 'bg-surface',
  applied: 'bg-blue-500',
  phone_screen: 'bg-yellow-500',
  interview: 'bg-purple-500',
  offer: 'bg-green-500',
  rejected: 'bg-red-500',
  withdrawn: 'bg-slate-500',
}

export default function ApplicationStats({ stats }: Props) {
  const total = APPLICATION_STATUSES.reduce((sum, status) => sum + (stats[status] ?? 0), 0)

  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-fg">Pipeline</h2>
          <p className="text-xs text-fg-muted">{total} tracked applications</p>
        </div>
        <span className="rounded-full bg-primary-900/20 px-3 py-1 text-xs font-semibold text-accent-text">
          Live tracker
        </span>
      </div>

      <div className="flex h-3 overflow-hidden rounded-full bg-track">
        {total === 0 ? (
          <div className="h-full w-full bg-surface" />
        ) : (
          APPLICATION_STATUSES.map((status) => {
            const count = stats[status] ?? 0
            if (count === 0) return null
            return (
              <div
                key={status}
                className={segmentClasses[status]}
                style={{ width: `${(count / total) * 100}%` }}
                title={`${STATUS_META[status].label}: ${count}`}
              />
            )
          })
        )}
      </div>

      <div className="mt-4 grid grid-cols-4 gap-3 lg:grid-cols-7">
        {APPLICATION_STATUSES.map((status) => (
          <div key={status} className="rounded-xl bg-surface px-3 py-2">
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${segmentClasses[status]}`} />
              <span className="truncate text-xs font-medium text-fg-muted">
                {STATUS_META[status].label}
              </span>
            </div>
            <p className="mt-1 text-lg font-bold text-fg">{stats[status] ?? 0}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
