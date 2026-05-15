import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatCompactCurrency, titleCase } from '../../../utils/formatters'
import type { SalaryInsightItem } from '../../../types'

interface Props {
  data: SalaryInsightItem[]
}

export default function SalaryInsightsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 10).map((item) => ({
        category: titleCase(item.dimension_value),
        p25: item.p25_salary ?? item.min_salary_floor ?? 0,
        median: item.p50_salary ?? item.avg_salary ?? 0,
        p75: item.p75_salary ?? item.max_salary_ceiling ?? 0,
        jobs: item.job_count,
      })),
    [data],
  )
  const average =
    chartData.length > 0
      ? chartData.reduce((sum, item) => sum + item.median, 0) / chartData.length
      : 0

  return (
    <>
      <div className="h-48 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 24, left: 0, bottom: 56 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
          <XAxis dataKey="category" angle={-35} textAnchor="end" height={72} tick={{ fontSize: 11, fill: '#6b7280' }} interval={0} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis tickFormatter={(value) => formatCompactCurrency(Number(value))} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, name) => [formatCompactCurrency(Number(value)), titleCase(String(name))]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <ReferenceLine y={average} stroke="#6366f1" strokeDasharray="3 3" />
          <Bar dataKey="p25" fill="#e5e7eb" stackId="salary" />
          <Bar dataKey="median" fill="#4f46e5" stackId="salary" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="salary-insights-desc" className="sr-only">
        Bar chart comparing salary percentiles across market segments.
      </p>
    </>
  )
}
