import { useMemo } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatCompactCurrency, formatNumber, formatPeriod } from '../../../utils/formatters'
import type { HiringPatternPoint } from '../../../types'

interface Props {
  data: HiringPatternPoint[]
}

export default function HiringPatternsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.map((point) => ({
        period: point.period,
        jobs: point.job_count,
        remote: point.remote_percentage,
        salary: point.avg_salary,
      })),
    [data],
  )

  return (
    <>
      <div className="h-48 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="analyticsJobsGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis dataKey="period" tickFormatter={formatPeriod} tick={CHART_AXIS_TICK} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            labelFormatter={(label) => formatPeriod(String(label))}
            formatter={(value, name, props) => {
              if (name === 'jobs') {
                return [`${formatNumber(Number(value))} jobs, ${formatCompactCurrency(props.payload.salary)} avg salary`, 'Posted']
              }
              return [String(value), String(name)]
            }}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '5 5' }}
          />
          <Area type="monotone" dataKey="jobs" stroke="#6366f1" strokeWidth={2} fill="url(#analyticsJobsGradient)" dot={false} activeDot={{ r: 4, fill: '#6366f1' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p id="hiring-patterns-desc" className="sr-only">
        Area chart showing job posting volume over time.
      </p>
    </>
  )
}
