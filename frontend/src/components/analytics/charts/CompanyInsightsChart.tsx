import { useMemo } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import { CATEGORY_AXIS_WIDTH } from './chartHelpers'
import { CategoryTick } from './chartParts'
import type { CompanyInsight } from '../../../types'

interface Props {
  data: CompanyInsight[]
}

export default function CompanyInsightsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 10).map((company) => ({
        name: company.company_name,
        count: company.total_jobs,
        remote: company.remote_percentage,
        velocity: company.hiring_velocity,
      })),
    [data],
  )

  return (
    <>
      <div className="h-64 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 16, left: 8, bottom: 5 }}>
          <XAxis type="number" tick={CHART_AXIS_TICK} axisLine={{ stroke: 'var(--glass-border-strong)' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={CATEGORY_AXIS_WIDTH} interval={0} tick={<CategoryTick />} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs, ${formatPercentage(Number(props.payload.remote))} remote`,
              'Open positions',
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="company-insights-desc" className="sr-only">
        Bar chart showing companies with the highest hiring volume.
      </p>
    </>
  )
}
