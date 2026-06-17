import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowRightIcon, ArrowTrendingUpIcon, FireIcon } from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'
import { fetchApplicationAnalytics } from '../../services/applicationsApi'
import type { WeeklyApplicationCount } from '../../types/application'

function formatWeek(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (value === 0) return
    const start = performance.now()
    const duration = 900
    function step(now: number) {
      const progress = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(ease * value))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [value])

  return <>{display}</>
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function GlowDot(props: any) {
  const { cx, cy, index, dataLength } = props
  if (index !== dataLength - 1) return null
  return (
    <g>
      <circle cx={cx} cy={cy} r={10} fill="#6366f1" fillOpacity={0.15} />
      <circle cx={cx} cy={cy} r={6} fill="#6366f1" fillOpacity={0.3} />
      <circle cx={cx} cy={cy} r={4} fill="#6366f1" />
      <circle cx={cx} cy={cy} r={4} fill="white" fillOpacity={0.4} />
    </g>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-[rgba(8,145,178,0.20)] bg-white/[0.04] px-4 py-3 shadow-xl">
      <p className="text-xs text-white/45">{formatWeek(String(label))}</p>
      <p className="mt-0.5 text-lg font-bold text-cyan-300">
        {payload[0].value as number}
        <span className="ml-1 text-xs font-normal text-white/45">applications</span>
      </p>
    </div>
  )
}

export default function DashboardActivityChart() {
  const [data, setData] = useState<WeeklyApplicationCount[]>([])
  const [loading, setLoading] = useState(true)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    fetchApplicationAnalytics()
      .then((analytics) => {
        setData(analytics.weekly_counts.slice(-12))
        setLoading(false)
        setTimeout(() => setVisible(true), 80)
      })
      .catch(() => setLoading(false))
  }, [])

  const total = data.reduce((s, d) => s + d.count, 0)
  const thisWeek = data[data.length - 1]?.count ?? 0
  const bestWeek = Math.max(...data.map((d) => d.count), 0)
  const streak = (() => {
    let s = 0
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i].count > 0) s++
      else break
    }
    return s
  })()

  const chartData = data.map((d, i) => ({ ...d, index: i, dataLength: data.length }))

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 ">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-white/90 ">Activity</h2>
          <p className="mt-0.5 text-xs text-white/45">Applications sent over the last 12 weeks</p>
        </div>
        <Link
          to="/applications?tab=stats"
          className="flex shrink-0 items-center gap-1 text-xs font-medium text-cyan-300 text-cyan-300"
        >
          Full stats <ArrowRightIcon className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Summary stats */}
      <div className="mb-5 grid grid-cols-3 divide-x divide-white/10 ">
        {[
          { label: 'Total sent', value: total, icon: null },
          { label: 'This week', value: thisWeek, icon: null },
          { label: 'Best week', value: bestWeek, icon: null },
        ].map(({ label, value }) => (
          <div key={label} className="px-4 first:pl-0 last:pr-0">
            <p className="text-xs text-white/45">{label}</p>
            <p className="mt-0.5 text-2xl font-bold text-white/90 ">
              {loading ? (
                <span className="inline-block h-7 w-10 animate-pulse rounded bg-white/[0.04]" />
              ) : (
                <AnimatedNumber value={value} />
              )}
            </p>
          </div>
        ))}
      </div>

      {/* Chart */}
      {loading ? (
        <div className="flex h-40 items-end gap-2 px-1">
          {[40, 65, 30, 80, 55, 90, 45, 70, 60, 85, 50, 75].map((h, i) => (
            <div
              key={i}
              className="flex-1 animate-pulse rounded-t-sm bg-[rgba(8,145,178,0.15)]"
              style={{ height: `${h}%`, animationDelay: `${i * 60}ms` }}
            />
          ))}
        </div>
      ) : total === 0 ? (
        <div className="flex h-40 flex-col items-center justify-center gap-2 rounded-xl bg-white/[0.03] ">
          <ArrowTrendingUpIcon className="h-8 w-8 text-white/45" />
          <p className="text-xs text-white/45">Start tracking applications to see your trend</p>
        </div>
      ) : (
        <div
          className="h-40 w-full transition-opacity duration-700"
          style={{ opacity: visible ? 1 : 0 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 4, left: -28, bottom: 0 }}>
              <defs>
                <linearGradient id="activityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="week_start"
                tickFormatter={formatWeek}
                tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)' }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)' }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#6366f1"
                strokeWidth={2.5}
                fill="url(#activityGradient)"
                animationBegin={0}
                animationDuration={1200}
                animationEasing="ease-out"
                dot={(props) => (
                  <GlowDot key={props.index} {...props} dataLength={chartData.length} />
                )}
                activeDot={{ r: 5, fill: '#6366f1', stroke: 'white', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Streak badge */}
      {streak >= 2 && (
        <div className="mt-4 flex items-center gap-1.5 rounded-xl bg-[rgba(245,158,11,0.14)] px-3 py-2 ">
          <FireIcon className="h-4 w-4 text-orange-500" />
          <p className="text-xs font-medium text-amber-300 ">
            {streak}-week streak — keep it up!
          </p>
        </div>
      )}
    </div>
  )
}
