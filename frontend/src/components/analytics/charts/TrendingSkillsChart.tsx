import { useMemo } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import { CATEGORY_AXIS_WIDTH } from './chartHelpers'
import { CategoryTick } from './chartParts'
import type { SkillTrend } from '../../../types'

interface Props {
  data: SkillTrend[]
}

export default function TrendingSkillsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 10).map((skill) => ({
        name: skill.skill,
        count: skill.frequency,
        percentage: skill.frequency_pct,
      })),
    [data],
  )

  return (
    <>
      <div className="h-64 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 16, left: 8, bottom: 5 }}>
          <XAxis type="number" tick={{ fontSize: 12, fill: 'var(--text-3)' }} axisLine={{ stroke: 'var(--glass-border-strong)' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={CATEGORY_AXIS_WIDTH} interval={0} tick={<CategoryTick />} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(Number(props.payload.percentage))})`,
              'Demand',
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="trending-skills-desc" className="sr-only">
        Bar chart showing the most in-demand skills by job posting count.
      </p>
    </>
  )
}
