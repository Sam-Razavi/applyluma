import { useCallback, useEffect, useState } from 'react'
import {
  ArrowPathIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  BriefcaseIcon,
  ChartBarIcon,
  CodeBracketIcon,
  CurrencyDollarIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  analyticsApi,
  type AnalyticsOverview,
  type CompanyStat,
  type DailyJobCount,
  type RecentJob,
  type SkillStat,
} from '../services/api'

// ── Palette ───────────────────────────────────────────────────────────────────

const C = {
  indigo: '#6366f1',
  emerald: '#10b981',
  amber: '#f59e0b',
  rose: '#f43f5e',
  sky: '#0ea5e9',
  violet: '#8b5cf6',
}

const PIE_COLORS = [C.emerald, C.indigo, C.amber]

const BAR_GRADIENT = [
  '#818cf8', '#6366f1', '#4f46e5', '#4338ca', '#3730a3',
  '#312e81', '#2e27a3', '#6366f1', '#818cf8', '#a5b4fc',
]

// ── Small helpers ─────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${Math.round(n / 1_000)}k`
  return `$${n}`
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center py-24">
      <div className="h-10 w-10 rounded-full border-4 border-indigo-200 border-t-indigo-600 animate-spin" />
    </div>
  )
}

function ChartCard({
  title,
  children,
  isEmpty,
}: {
  title: string
  children: React.ReactNode
  isEmpty?: boolean
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-5">{title}</h2>
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <ChartBarIcon className="h-8 w-8 mb-2" />
          <p className="text-sm">No data yet</p>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

interface MetricProps {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  iconBg: string
  iconColor: string
}

function MetricCard({ label, value, sub, icon: Icon, iconBg, iconColor }: MetricProps) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5 flex items-start gap-4">
      <div className={`${iconBg} rounded-xl p-3 flex-shrink-0`}>
        <Icon className={`h-5 w-5 ${iconColor}`} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="mt-1 text-2xl font-bold text-gray-900 truncate">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-gray-500">{sub}</p>}
      </div>
    </div>
  )
}

function TrendBadge({ trend }: { trend: string }) {
  if (trend === 'up')
    return (
      <span className="inline-flex items-center gap-0.5 text-emerald-600 text-xs font-medium">
        <ArrowTrendingUpIcon className="h-3.5 w-3.5" /> up
      </span>
    )
  if (trend === 'down')
    return (
      <span className="inline-flex items-center gap-0.5 text-rose-500 text-xs font-medium">
        <ArrowTrendingDownIcon className="h-3.5 w-3.5" /> down
      </span>
    )
  return <span className="text-gray-400 text-xs">stable</span>
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Analytics() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [companies, setCompanies] = useState<CompanyStat[]>([])
  const [skills, setSkills] = useState<SkillStat[]>([])
  const [jobsOverTime, setJobsOverTime] = useState<DailyJobCount[]>([])
  const [recentJobs, setRecentJobs] = useState<RecentJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [ov, co, sk, jt, rj] = await Promise.all([
        analyticsApi.overview(),
        analyticsApi.topCompanies(10),
        analyticsApi.topSkills(10),
        analyticsApi.jobsOverTime(30),
        analyticsApi.recentJobs(20),
      ])
      setOverview(ov)
      setCompanies(co)
      setSkills(sk)
      setJobsOverTime(jt)
      setRecentJobs(rj)
      setLastRefresh(new Date())
    } catch {
      setError('Failed to load analytics data. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // ── Salary label ─────────────────────────────────────────────────────────
  const salaryLabel =
    overview?.avg_salary_min || overview?.avg_salary_max
      ? `${fmt(overview.avg_salary_min)} – ${fmt(overview.avg_salary_max)}`
      : 'No data'

  // ── Remote donut data ─────────────────────────────────────────────────────
  const remote = overview?.remote_percentage ?? 0
  const pieData = [
    { name: 'Remote', value: Math.round(remote) },
    { name: 'On-site', value: Math.round(100 - remote) },
  ]

  const hasData = overview && overview.total_jobs > 0

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Market Analytics</h1>
          <p className="mt-1 text-sm text-gray-500">
            Aggregated from Remotive &amp; The Muse · updated{' '}
            {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={fetchAll}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200
                     text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed self-start sm:self-auto"
        >
          <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* ── Loading ─────────────────────────────────────────────────────────── */}
      {loading && <Spinner />}

      {/* ── Error ───────────────────────────────────────────────────────────── */}
      {!loading && error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 px-5 py-4 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────────────────── */}
      {!loading && !error && !hasData && (
        <div className="bg-white rounded-2xl border border-gray-200 flex flex-col items-center py-24 text-center px-6">
          <ChartBarIcon className="h-14 w-14 text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No job market data yet</h2>
          <p className="text-gray-500 max-w-md">
            The Airflow pipeline scrapes jobs daily at 2 AM UTC. Once it runs, your analytics
            will appear here automatically.
          </p>
        </div>
      )}

      {/* ── Dashboard content ───────────────────────────────────────────────── */}
      {!loading && !error && hasData && (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Total Jobs Scraped"
              value={overview!.total_jobs.toLocaleString()}
              sub="non-duplicate postings"
              icon={BriefcaseIcon}
              iconBg="bg-indigo-50"
              iconColor="text-indigo-600"
            />
            <MetricCard
              label="Remote Jobs"
              value={`${overview!.remote_percentage}%`}
              sub="of all postings"
              icon={GlobeAltIcon}
              iconBg="bg-emerald-50"
              iconColor="text-emerald-600"
            />
            <MetricCard
              label="Avg Salary Range"
              value={salaryLabel}
              sub="across postings with salary"
              icon={CurrencyDollarIcon}
              iconBg="bg-amber-50"
              iconColor="text-amber-600"
            />
            <MetricCard
              label="Top Skill"
              value={overview!.top_skill ?? '—'}
              sub="most in-demand"
              icon={CodeBracketIcon}
              iconBg="bg-violet-50"
              iconColor="text-violet-600"
            />
          </div>

          {/* Charts row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Top Companies */}
            <ChartCard title="Top 10 Companies" isEmpty={companies.length === 0}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  layout="vertical"
                  data={companies}
                  margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f3f4f6" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="company"
                    width={110}
                    tick={{ fontSize: 11, fill: '#374151' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: '#f5f3ff' }}
                    contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                    formatter={(v: any) => [v, 'Jobs']}
                  />
                  <Bar dataKey="job_count" radius={[0, 4, 4, 0]}>
                    {companies.map((_, i) => (
                      <Cell key={i} fill={BAR_GRADIENT[i % BAR_GRADIENT.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Top Skills */}
            <ChartCard title="Top 10 Skills" isEmpty={skills.length === 0}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={skills}
                  margin={{ top: 0, right: 8, bottom: 40, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis
                    dataKey="skill"
                    tick={{ fontSize: 10, fill: '#374151' }}
                    tickLine={false}
                    axisLine={false}
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ fill: '#f5f3ff' }}
                    contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                    formatter={(v: any) => [v, 'Mentions']}
                  />
                  <Bar dataKey="mention_count" fill={C.indigo} radius={[4, 4, 0, 0]}>
                    {skills.map((_, i) => (
                      <Cell key={i} fill={i < 3 ? C.violet : C.indigo} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {/* Trend table under chart */}
              <div className="mt-3 divide-y divide-gray-100">
                {skills.slice(0, 5).map((s) => (
                  <div key={s.skill} className="flex items-center justify-between py-1.5">
                    <span className="text-xs text-gray-700 font-medium">{s.skill}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-500">{s.mention_count} jobs</span>
                      <TrendBadge trend={s.trend} />
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          </div>

          {/* Charts row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Jobs Over Time */}
            <ChartCard title="Jobs Scraped — Last 30 Days" isEmpty={jobsOverTime.length === 0}>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart
                  data={jobsOverTime}
                  margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={fmtDate}
                    tick={{ fontSize: 10, fill: '#9ca3af' }}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                    labelFormatter={(label: any) => fmtDate(String(label))}
                    formatter={(v: any) => [v, 'Jobs']}
                  />
                  <Line
                    type="monotone"
                    dataKey="job_count"
                    stroke={C.indigo}
                    strokeWidth={2}
                    dot={{ fill: C.indigo, r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Remote Distribution */}
            <ChartCard title="Remote vs On-site">
              <div className="flex items-center justify-center gap-10">
                <ResponsiveContainer width={180} height={180}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                      startAngle={90}
                      endAngle={-270}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i]} stroke="none" />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                      formatter={(v: any) => [`${v}%`, '']}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-4">
                  {pieData.map((entry, i) => (
                    <div key={entry.name} className="flex items-center gap-3">
                      <span
                        className="h-3 w-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: PIE_COLORS[i] }}
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{entry.name}</p>
                        <p className="text-2xl font-bold" style={{ color: PIE_COLORS[i] }}>
                          {entry.value}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </ChartCard>
          </div>

          {/* Recent Jobs Table */}
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Recent Job Postings</h2>
              <p className="text-xs text-gray-500 mt-0.5">Latest {recentJobs.length} scraped listings</p>
            </div>

            {recentJobs.length === 0 ? (
              <div className="flex flex-col items-center py-16 text-gray-400">
                <BriefcaseIcon className="h-8 w-8 mb-2" />
                <p className="text-sm">No recent jobs</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Company', 'Title', 'Skills', 'Remote', 'Posted', 'Link'].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {recentJobs.map((job) => {
                      const skills = job.extracted_skills ?? []
                      const shown = skills.slice(0, 3)
                      const extra = skills.length - shown.length
                      return (
                        <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                            {job.company}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700 max-w-[200px] truncate">
                            {job.title}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {shown.map((s) => (
                                <span
                                  key={s}
                                  className="inline-block px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-medium"
                                >
                                  {s}
                                </span>
                              ))}
                              {extra > 0 && (
                                <span className="inline-block px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-xs">
                                  +{extra}
                                </span>
                              )}
                              {skills.length === 0 && (
                                <span className="text-xs text-gray-400">—</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                                job.remote_allowed
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              {job.remote_allowed ? 'Remote' : 'On-site'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                            {fmtRelative(job.scraped_at)}
                          </td>
                          <td className="px-4 py-3">
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                            >
                              View →
                            </a>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
