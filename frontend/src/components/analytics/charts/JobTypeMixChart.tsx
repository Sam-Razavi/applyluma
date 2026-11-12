import { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import { legendLabel } from './chartHelpers'
import { buildJobTypeSlices } from './jobTypeMix'
import type { JobTypeMixItem } from '../../../types'

interface Props {
  data: JobTypeMixItem[]
}

export default function JobTypeMixChart({ data }: Props) {
  const chartData = useMemo(() => buildJobTypeSlices(data), [data])
  const totalJobs = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius="42%"
            outerRadius="70%"
            paddingAngle={3}
            dataKey="value"
            nameKey="name"
            label={(entry) => {
              const pct = Math.round((entry.value / Math.max(totalJobs, 1)) * 100)
              // Only label slices big enough to avoid overlapping callouts.
              return pct >= 5 ? `${pct}%` : ''
            }}
            labelLine={false}
          >
            {chartData.map((entry, index) => (
              <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(props.payload.percentage)})`,
              props.payload.name,
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
          <Legend itemSorter={null} formatter={legendLabel} verticalAlign="bottom" height={84} wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p id="job-type-mix-desc" className="sr-only">
        Pie chart showing job count distribution by employment type and remote status.
      </p>
    </>
  )
}
