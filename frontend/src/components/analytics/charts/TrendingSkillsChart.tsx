import { useMemo } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_COLORS, CHART_DARK_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import type { SkillTrend } from '../../../types'

interface Props {
  data: SkillTrend[]
}

export default function TrendingSkillsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 12).map((skill) => ({
        name: skill.skill,
        count: skill.frequency,
        percentage: skill.frequency_pct,
      })),
    [data],
  )

  return (
    <>
      <div className="h-48 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 24, left: 80, bottom: 5 }}>
          <XAxis type="number" tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={110} tick={CHART_DARK_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(Number(props.payload.percentage))})`,
              'Demand',
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="trending-skills-desc" className="sr-only">
        Bar chart showing the most in-demand skills by job posting count.
      </p>
    </>
  )
}
