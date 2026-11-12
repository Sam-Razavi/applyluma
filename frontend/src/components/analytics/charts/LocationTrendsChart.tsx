import { useMemo } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import { CATEGORY_AXIS_WIDTH } from './chartHelpers'
import { CategoryTick } from './chartParts'
import type { LocationTrend } from '../../../types'

interface Props {
  data: LocationTrend[]
}

export default function LocationTrendsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 10).map((location) => ({
        name: location.location,
        count: location.job_count,
        share: location.pct_of_total,
        remote: location.remote_percentage,
      })),
    [data],
  )

  return (
    <>
      <div className="h-64 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 16, left: 8, bottom: 5 }}>
          <XAxis type="number" allowDecimals={false} tick={CHART_AXIS_TICK} axisLine={{ stroke: 'var(--glass-border-strong)' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={CATEGORY_AXIS_WIDTH} interval={0} tick={<CategoryTick />} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(Number(props.payload.share))} of all), ${formatPercentage(Number(props.payload.remote))} remote`,
              props.payload.name,
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Bar dataKey="count" fill={CHART_COLORS[2]} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="location-trends-desc" className="sr-only">
        Bar chart showing the locations with the most job postings.
      </p>
    </>
  )
}
