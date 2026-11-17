import { useEffect, useMemo, useState } from 'react'
import ChartCard from '../analytics/ChartCard'
import LoadingSkeleton from '../analytics/LoadingSkeleton'
import { fetchApplicationAnalytics, fetchApplicationInsights } from '../../services/applicationsApi'
import type { ApplicationAnalytics, ApplicationInsights } from '../../types/application'
import ApplicationsOverTimeChart from './ApplicationsOverTimeChart'
import FunnelChart from './FunnelChart'
import SourceBreakdownChart from './SourceBreakdownChart'
import {
  BarList,
  CvTable,
  SalarySummary,
  SourceTable,
  StageProgress,
  StatTile,
  UpcomingList,
  WeekdayBars,
} from './stats/StatsPanels'
import { buildSummary, pct, weeklyChangePct } from './stats/statsSummary'

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="pt-2">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      <p className="text-sm text-fg-muted">{subtitle}</p>
    </div>
  )
}

export default function PersonalAnalytics() {
  const [analytics, setAnalytics] = useState<ApplicationAnalytics | null>(null)
  // Insights are an extra layer: if they fail the original charts still show.
  const [insights, setInsights] = useState<ApplicationInsights | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      fetchApplicationAnalytics(),
      fetchApplicationInsights().catch(() => null),
    ])
      .then(([base, extra]) => {
        if (cancelled) return
        setAnalytics(base)
        setInsights(extra)
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
  const summary = useMemo(
    () => (analytics && insights ? buildSummary(analytics, insights) : []),
    [analytics, insights],
  )

  if (loading) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {[...Array(4)].map((_, index) => (
          <section key={index} className="rounded-lg border border-line bg-surface p-6 shadow-sm">
            <LoadingSkeleton />
          </section>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-chip-danger bg-chip-danger px-6 py-10 text-center">
        <h2 className="text-sm font-semibold text-chip-danger-fg">Analytics unavailable</h2>
        <p className="mt-1 text-sm text-chip-danger-fg">{error}</p>
      </div>
    )
  }

  if (!analytics || totalApplications === 0) {
    return (
      <div className="rounded-2xl border border-line bg-surface px-6 py-16 text-center">
        <h2 className="text-sm font-semibold text-fg">No personal stats yet</h2>
        <p className="mt-1 text-sm text-fg-muted">
          Add applications to populate your funnel, response rates, and source breakdown.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {insights && (
        <>
          <section
            aria-label="Summary"
            className="rounded-2xl border border-line bg-surface p-5 shadow-sm"
            style={{ borderLeft: '4px solid var(--accent)' }}
          >
            <h2 className="text-sm font-semibold text-fg">Your search at a glance</h2>
            <ul className="mt-2 space-y-1.5 text-sm text-fg-muted">
              {summary.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Tracked in total" value={String(insights.total)} hint={`${insights.wishlist} on wishlist`} />
            <StatTile
              label="Still in play"
              value={String(insights.active)}
              hint={`${insights.closed} rejected or withdrawn`}
            />
            <StatTile
              label="Sent, last 7 days"
              value={String(insights.applied_last_7d)}
              trend={weeklyChangePct(insights)}
              hint={`${insights.applied_last_30d} in the last 30 days`}
            />
            <StatTile
              label="Waiting for a reply"
              value={String(insights.awaiting_reply)}
              hint={`No answer after ${insights.awaiting_reply_days}+ days`}
              tone={insights.awaiting_reply > 0 ? 'warn' : 'default'}
            />
            <StatTile
              label="Reply rate"
              value={pct(analytics.response_rate)}
              hint="Sent applications that got any answer"
            />
            <StatTile
              label="Interview rate"
              value={pct(insights.interview_rate)}
              hint="Sent applications that reached an interview"
            />
            <StatTile label="Offer rate" value={pct(analytics.offer_rate)} hint="Sent applications that ended in an offer" />
            <StatTile
              label="Typical reply time"
              value={analytics.average_response_days == null ? 'n/a' : `${analytics.average_response_days.toFixed(1)} days`}
              hint="From applying to the first answer"
            />
          </div>
        </>
      )}

      <SectionTitle title="Progress" subtitle="Where your applications stand and how fast you are sending them." />
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Application Funnel"
          subtitle="Counts by current pipeline status"
          empty={analytics.funnel.every((item) => item.count === 0)}
        >
          <FunnelChart data={analytics.funnel} />
        </ChartCard>

        <ChartCard
          title="Applications Over Time"
          subtitle="Weekly volume across the past 12 weeks"
          empty={analytics.weekly_counts.every((item) => item.count === 0)}
        >
          <ApplicationsOverTimeChart data={analytics.weekly_counts} />
        </ChartCard>

        {insights && (
          <>
            <ChartCard title="How far applications get" subtitle="Share of sent applications reaching each stage">
              <StageProgress stages={insights.stage_reach} submitted={insights.submitted} />
            </ChartCard>

            <ChartCard title="Coming up" subtitle="Interviews and wishlist deadlines in the next 2 weeks">
              <UpcomingList items={insights.upcoming} />
            </ChartCard>
          </>
        )}
      </div>

      {insights && (
        <>
          <SectionTitle title="What is working" subtitle="Compare where and how you apply to see what gets replies." />
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Results by source" subtitle="Where you found the job, and how often it replied">
              <SourceTable rows={insights.source_performance} />
            </ChartCard>

            <ChartCard title="Results by CV" subtitle="Which CV got the most replies">
              <CvTable rows={insights.cv_performance} />
            </ChartCard>

            <ChartCard
              title="Source Breakdown"
              subtitle="Top sources by application count"
              empty={analytics.top_sources.length === 0}
            >
              <SourceBreakdownChart data={analytics.top_sources} />
            </ChartCard>

            <ChartCard title="When you apply" subtitle="Applications sent per weekday">
              <WeekdayBars days={insights.weekday_counts} />
            </ChartCard>
          </div>

          <SectionTitle title="The jobs you chase" subtitle="Work style, places, employers and pay." />
          <div className="grid gap-4 lg:grid-cols-3">
            <ChartCard title="Work style" subtitle="Remote, hybrid or on-site">
              <BarList
                rows={insights.work_modes.map((m) => ({ label: m.label, value: m.count }))}
                emptyText="Set remote / hybrid / on-site on your applications."
              />
            </ChartCard>

            <ChartCard title="Top locations" subtitle="Where the jobs are">
              <BarList
                rows={insights.top_locations.map((l) => ({ label: l.label, value: l.count }))}
                emptyText="Add a location to your applications."
              />
            </ChartCard>

            <ChartCard title="Repeat employers" subtitle="Companies you applied to more than once">
              <BarList
                rows={insights.top_companies.map((c) => ({ label: c.label, value: c.count }))}
                emptyText="No company appears more than once."
              />
            </ChartCard>

            <ChartCard title="Salary" subtitle="Midpoint of the ranges you saved" className="lg:col-span-3">
              <SalarySummary
                buckets={analytics.salary_distribution}
                median={insights.salary_median}
                min={insights.salary_min}
                max={insights.salary_max}
                sample={insights.salary_sample}
              />
            </ChartCard>
          </div>
        </>
      )}
    </div>
  )
}
