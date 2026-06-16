import { AcademicCapIcon, ArrowTrendingUpIcon, TrophyIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import { formatPercentage } from '../../../utils/formatters'
import type { JobMarketHealth } from '../../../types'

interface Props {
  data: JobMarketHealth | null
  loading: boolean
  error: string | null
}

export default function JobMarketHealthCard({ data, loading, error }: Props) {
  if (loading || error || !data) {
    return (
      <section className="rounded-lg border border-white/10 bg-white/[0.04] p-6 shadow-sm" aria-label="Market health" tabIndex={0}>
        <h2 className="mb-4 text-base font-semibold text-white/90">Market Health</h2>
        {loading ? (
          <div className="animate-pulse space-y-3" aria-hidden="true">
            <div className="h-16 rounded bg-white/[0.06]" />
            <div className="h-16 rounded bg-white/[0.06]" />
            <div className="h-16 rounded bg-white/[0.06]" />
          </div>
        ) : (
          <p className="text-sm text-white/30">{error ?? 'No data available'}</p>
        )}
      </section>
    )
  }

  const metrics = [
    { icon: UserGroupIcon, label: 'Senior Roles', value: formatPercentage(data.senior_role_pct, 0), color: 'text-cyan-300 bg-[rgba(8,145,178,0.15)]' },
    { icon: TrophyIcon, label: 'Mid-Level', value: formatPercentage(data.mid_role_pct, 0), color: 'text-cyan-300 bg-[rgba(8,145,178,0.15)]' },
    { icon: ArrowTrendingUpIcon, label: 'Junior Roles', value: formatPercentage(data.junior_role_pct, 0), color: 'text-emerald-300 bg-[rgba(52,195,143,0.14)]' },
    { icon: AcademicCapIcon, label: 'Avg Skills/Job', value: data.avg_skills_per_job.toFixed(1), color: 'text-amber-300 bg-[rgba(245,158,11,0.14)]' },
  ]

  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.04] p-6 shadow-sm transition-shadow duration-200 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2" aria-label="Market health" tabIndex={0}>
      <h2 className="mb-6 text-base font-semibold text-white/90">Market Health</h2>
      <div className="space-y-3">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <div key={metric.label} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 p-4 transition-all duration-200 hover:border-primary-500 hover:shadow-sm">
              <div className="flex min-w-0 items-center gap-3">
                <div className={`rounded-lg p-2.5 ${metric.color}`}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <span className="truncate text-sm font-medium text-white/55">{metric.label}</span>
              </div>
              <span className="text-xl font-semibold text-white/90">{metric.value}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
