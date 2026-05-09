import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatCompactCurrency, formatNumber, formatPercentage, titleCase } from '../../../utils/formatters'
import type { ExperienceLevelBreakdown } from '../../../types'

interface Props {
  data: ExperienceLevelBreakdown[]
}

export default function ExperienceLevelsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.map((level) => ({
        level: titleCase(level.level),
        count: level.job_count,
        percentage: level.pct_of_total,
        salary: level.avg_salary_min && level.avg_salary_max ? (level.avg_salary_min + level.avg_salary_max) / 2 : null,
      })),
    [data],
  )

  return (
    <>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 20, right: 24, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis dataKey="level" tick={CHART_AXIS_TICK} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(props.payload.percentage)}), ${formatCompactCurrency(props.payload.salary)} avg salary`,
              'Count',
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p id="experience-levels-desc" className="sr-only">
        Bar chart showing job postings by seniority level.
      </p>
    </>
  )
}
