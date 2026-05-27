import { useEffect, useMemo, useState } from 'react'
import ChartCard from '../analytics/ChartCard'
import LoadingSkeleton from '../analytics/LoadingSkeleton'
import { fetchApplicationAnalytics } from '../../services/applicationsApi'
import type { ApplicationAnalytics } from '../../types/application'
import ApplicationsOverTimeChart from './ApplicationsOverTimeChart'
import FunnelChart from './FunnelChart'
import ResponseRateCard from './ResponseRateCard'
import SourceBreakdownChart from './SourceBreakdownChart'

export default function PersonalAnalytics() {
  const [analytics, setAnalytics] = useState<ApplicationAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchApplicationAnalytics()
      .then((data) => {
        if (!cancelled) setAnalytics(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load application analytics')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const totalApplications = useMemo(
    () => analytics?.funnel.reduce((sum, item) => sum + item.count, 0) ?? 0,
    [analytics],
  )

  if (loading) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {[...Array(4)].map((_, index) => (
          <section key={index} className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <LoadingSkeleton />
          </section>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center">
        <h2 className="text-sm font-semibold text-red-800">Analytics unavailable</h2>
        <p className="mt-1 text-sm text-red-700">{error}</p>
      </div>
    )
  }

  if (!analytics || totalApplications === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-16 text-center">
        <h2 className="text-sm font-semibold text-gray-900">No personal stats yet</h2>
        <p className="mt-1 text-sm text-gray-400">
          Add applications to populate your funnel, response rates, and source breakdown.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard
        title="Application Funnel"
        subtitle="Counts by current pipeline status"
        empty={analytics.funnel.every((item) => item.count === 0)}
      >
        <FunnelChart data={analytics.funnel} />
      </ChartCard>

      <ChartCard
        title="Response Rates"
        subtitle="Responses and offers from submitted applications"
      >
        <ResponseRateCard
          responseRate={analytics.response_rate}
          offerRate={analytics.offer_rate}
          averageResponseDays={analytics.average_response_days}
        />
      </ChartCard>

      <ChartCard
        title="Applications Over Time"
        subtitle="Weekly volume across the past 12 weeks"
        empty={analytics.weekly_counts.every((item) => item.count === 0)}
      >
        <ApplicationsOverTimeChart data={analytics.weekly_counts} />
      </ChartCard>

      <ChartCard
        title="Source Breakdown"
        subtitle="Top sources by application count"
        empty={analytics.top_sources.length === 0}
      >
        <SourceBreakdownChart data={analytics.top_sources} />
      </ChartCard>
    </div>
  )
}
