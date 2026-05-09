import { useMemo } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_COLORS, CHART_DARK_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatCompactCurrency, formatNumber } from '../../../utils/formatters'
import type { SalaryBySkill } from '../../../types'

interface Props {
  data: SalaryBySkill[]
}

export default function SalaryBySkillChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      [...data]
        .filter((skill) => skill.avg_salary != null)
        .sort((a, b) => (b.avg_salary ?? 0) - (a.avg_salary ?? 0))
        .slice(0, 15)
        .map((skill) => ({
          name: skill.skill,
          salary: skill.avg_salary ?? 0,
          jobs: skill.job_count,
        })),
    [data],
  )

  return (
    <>
      <ResponsiveContainer width="100%" height={450}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 40, left: 140, bottom: 5 }}>
          <XAxis type="number" tickFormatter={(value) => formatCompactCurrency(Number(value))} tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={110} tick={CHART_DARK_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatCompactCurrency(Number(value))} across ${formatNumber(props.payload.jobs)} jobs`,
              'Avg salary',
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="salary" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p id="salary-by-skill-desc" className="sr-only">
        Horizontal bar chart showing top paying skills by average salary.
      </p>
    </>
  )
}
