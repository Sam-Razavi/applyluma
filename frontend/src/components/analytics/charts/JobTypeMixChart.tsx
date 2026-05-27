import { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage, titleCase } from '../../../utils/formatters'
import type { JobTypeMixItem } from '../../../types'

interface Props {
  data: JobTypeMixItem[]
}

export default function JobTypeMixChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.map((item) => ({
        name: `${titleCase(item.job_type)} / ${titleCase(item.remote_label)}`,
        value: item.job_count,
        percentage: item.pct_of_total,
      })),
    [data],
  )
  const totalJobs = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <>
      <div className="h-48 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="45%"
            innerRadius={54}
            outerRadius={98}
            paddingAngle={3}
            dataKey="value"
            nameKey="name"
            label={(entry) => `${Math.round((entry.value / Math.max(totalJobs, 1)) * 100)}%`}
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
          <Legend verticalAlign="bottom" height={60} wrapperStyle={{ fontSize: '12px', paddingTop: '16px' }} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p id="job-type-mix-desc" className="sr-only">
        Pie chart showing job count distribution by employment type and remote status.
      </p>
    </>
  )
}
