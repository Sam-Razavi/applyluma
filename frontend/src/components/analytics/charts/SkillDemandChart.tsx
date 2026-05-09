import { useMemo } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber } from '../../../utils/formatters'
import type { SkillDemand } from '../../../types'

interface Props {
  data: SkillDemand[]
}

export default function SkillDemandChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 8).map((skill) => ({
        skill: skill.skill,
        thisWeek: skill.mentions_this_week,
        lastWeek: skill.mentions_last_week,
        growth: skill.trending_score_pct,
      })),
    [data],
  )

  return (
    <>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 24, left: 0, bottom: 28 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis dataKey="skill" angle={-25} textAnchor="end" interval={0} tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, name) => [formatNumber(Number(value)), name === 'thisWeek' ? 'This week' : 'Last week']}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
          <Legend wrapperStyle={{ paddingTop: '16px', fontSize: '12px' }} iconType="circle" />
          <Line type="monotone" dataKey="thisWeek" name="This week" stroke={CHART_COLORS[0]} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="lastWeek" name="Last week" stroke={CHART_COLORS[1]} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
      <p id="skill-demand-desc" className="sr-only">
        Line chart comparing this week's and last week's mentions for growing skills.
      </p>
    </>
  )
}
