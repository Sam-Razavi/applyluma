import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { FadeIn } from '../../components/ui/FadeIn'
import {
  adminApi,
  type JobsBySourceItem,
  type JobsOverTimePoint,
  type PipelineHealth,
  type PipelineMetrics,
  type PipelineStage,
  type SourceHealth,
} from '../../services/adminApi'

type HealthRow = (PipelineStage | SourceHealth) & { label: string }

function formatLastRun(lastRun: string | null) {
  if (!lastRun) return 'never'
  return new Date(lastRun).toLocaleString()
}

function statusLabel(row: PipelineStage | SourceHealth) {
  if (row.healthy) return 'Healthy'
  return row.last_run ? 'Stale' : 'Missing'
}

function HealthStatus({ row }: { row: PipelineStage | SourceHealth }) {
  const healthy = row.healthy
  return (
    <div className={`flex items-center gap-2 text-sm font-semibold ${healthy ? 'text-chip-success-fg' : 'text-chip-danger-fg'}`}>
      <span className={`h-2.5 w-2.5 rounded-full ${healthy ? 'bg-green-500' : 'bg-red-500'}`} />
      {statusLabel(row)}
    </div>
  )
}

function LoadingCard() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 ">
      <div className="h-5 w-36 animate-pulse rounded bg-track " />
      <div className="mt-4 h-40 animate-pulse rounded-xl bg-track " />
    </div>
  )
}

function CountBadge({ count }: { count: number }) {
  return (
    <span className="rounded-full bg-primary-900/20 px-2.5 py-1 text-xs font-semibold text-accent-text ">
      {count.toLocaleString()}
    </span>
  )
}

export default function AdminPipeline() {
  const [health, setHealth] = useState<PipelineHealth | null>(null)
  const [jobsOverTime, setJobsOverTime] = useState<JobsOverTimePoint[]>([])
  const [jobsBySource, setJobsBySource] = useState<JobsBySourceItem[]>([])
  const [metrics, setMetrics] = useState<PipelineMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Pipeline Health - ApplyLuma'
    Promise.all([
      adminApi.getPipelineHealth(),
      adminApi.getJobsOverTime(),
      adminApi.getJobsBySource(),
      adminApi.getPipelineMetrics(),
    ])
      .then(([healthData, overTimeData, bySourceData, metricsData]) => {
        setHealth(healthData)
        setJobsOverTime(overTimeData)
        setJobsBySource(bySourceData)
        setMetrics(metricsData)
      })
      .catch(() => setError('Failed to load pipeline health'))
      .finally(() => setLoading(false))
  }, [])

  const healthRows = useMemo<HealthRow[]>(() => {
    if (!health) return []
    return [
      { ...health.raw_job_postings, label: 'Raw job postings' },
      { ...health.extracted_keywords, label: 'Extracted keywords' },
      { ...health.job_market_metrics, label: 'Job market metrics' },
      ...health.sources.map((source) => ({ ...source, label: source.source })),
    ]
  }, [health])

  return (
    <FadeIn>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-fg ">Pipeline Health</h1>
          <p className="mt-1 text-sm text-fg-subtle ">
            Monitor job ingestion freshness, source coverage, and latest market metrics.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-chip-danger bg-chip-danger p-4 text-sm text-chip-danger-fg">{error}</div>
        )}

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <LoadingCard />
            <LoadingCard />
            <LoadingCard />
            <LoadingCard />
          </div>
        ) : (
          <>
            <section className="rounded-2xl border border-line bg-surface p-5 ">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                Pipeline Health
              </h2>
              <div className="mt-4 divide-y divide-line ">
                {healthRows.map((row) => (
                  <div key={`${row.label}-${row.count}`} className="grid gap-3 py-4 sm:grid-cols-4 sm:items-center">
                    <div>
                      <p className="font-semibold text-fg ">{row.label}</p>
                      {'source' in row && (
                        <p className="text-xs text-fg-subtle ">Source</p>
                      )}
                    </div>
                    <p className="text-sm text-fg-muted ">{row.count.toLocaleString()} records</p>
                    <p className="text-sm text-fg-subtle ">Last run: {formatLastRun(row.last_run)}</p>
                    <HealthStatus row={row} />
                  </div>
                ))}
              </div>
            </section>

            <div className="grid gap-4 lg:grid-cols-2">
              <section className="rounded-2xl border border-line bg-surface p-5 ">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                  Jobs Over Time
                </h2>
                <div className="mt-4">
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={jobsOverTime} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.10)" />
                      <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }} tickLine={false} />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }} tickLine={false} />
                      <Tooltip />
                      <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>

              <section className="rounded-2xl border border-line bg-surface p-5 ">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                  Jobs by Source
                </h2>
                <div className="mt-4">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={jobsBySource} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.10)" />
                      <XAxis dataKey="source" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }} tickLine={false} />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 12 }} tickLine={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <section className="rounded-2xl border border-line bg-surface p-5 ">
                <p className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                  Remote Percentage
                </p>
                <p className="mt-3 text-4xl font-bold text-accent-text ">
                  {metrics?.remote_percentage == null ? '—' : `${metrics.remote_percentage}%`}
                </p>
                <p className="mt-1 text-xs text-fg-subtle ">
                  Latest metric date: {metrics?.metric_date ?? 'none'}
                </p>
              </section>

              <section className="rounded-2xl border border-line bg-surface p-5 ">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                  Top Skills
                </h2>
                <div className="mt-4 space-y-3">
                  {(metrics?.top_skills ?? []).map((item) => (
                    <div key={item.skill} className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-fg ">{item.skill}</span>
                      <CountBadge count={item.count} />
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-line bg-surface p-5 ">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted ">
                  Top Companies
                </h2>
                <div className="mt-4 space-y-3">
                  {(metrics?.top_companies ?? []).map((item) => (
                    <div key={item.company} className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-fg ">{item.company}</span>
                      <CountBadge count={item.count} />
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </FadeIn>
  )
}
