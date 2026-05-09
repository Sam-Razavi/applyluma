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
      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm" aria-label="Market health" tabIndex={0}>
        <h2 className="mb-4 text-base font-semibold text-gray-900">Market Health</h2>
        {loading ? (
          <div className="animate-pulse space-y-3" aria-hidden="true">
            <div className="h-16 rounded bg-gray-200" />
            <div className="h-16 rounded bg-gray-200" />
            <div className="h-16 rounded bg-gray-200" />
          </div>
        ) : (
          <p className="text-sm text-gray-500">{error ?? 'No data available'}</p>
        )}
      </section>
    )
  }

  const metrics = [
    { icon: UserGroupIcon, label: 'Senior Roles', value: formatPercentage(data.senior_role_pct, 0), color: 'text-blue-700 bg-blue-50' },
    { icon: TrophyIcon, label: 'Mid-Level', value: formatPercentage(data.mid_role_pct, 0), color: 'text-violet-700 bg-violet-50' },
    { icon: ArrowTrendingUpIcon, label: 'Junior Roles', value: formatPercentage(data.junior_role_pct, 0), color: 'text-green-600 bg-green-50' },
    { icon: AcademicCapIcon, label: 'Avg Skills/Job', value: data.avg_skills_per_job.toFixed(1), color: 'text-amber-700 bg-amber-50' },
  ]

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2" aria-label="Market health" tabIndex={0}>
      <h2 className="mb-6 text-base font-semibold text-gray-900">Market Health</h2>
      <div className="space-y-3">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <div key={metric.label} className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 p-4 transition-all duration-200 hover:border-primary-500 hover:shadow-sm">
              <div className="flex min-w-0 items-center gap-3">
                <div className={`rounded-lg p-2.5 ${metric.color}`}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <span className="truncate text-sm font-medium text-gray-700">{metric.label}</span>
              </div>
              <span className="text-xl font-semibold text-gray-900">{metric.value}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
