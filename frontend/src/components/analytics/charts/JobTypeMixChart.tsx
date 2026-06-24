import { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage, titleCase } from '../../../utils/formatters'
import type { JobTypeMixItem } from '../../../types'

interface Props {
  data: JobTypeMixItem[]
}

export default function JobTypeMixChart({ data }: Props) {
  const chartData = useMemo(() => {
    const mapped = data
      .map((item) => ({
        name: `${titleCase(item.job_type)} / ${titleCase(item.remote_label)}`,
        value: item.job_count,
        percentage: item.pct_of_total,
      }))
      .sort((a, b) => b.value - a.value)

    // Collapse the long tail of tiny segments into a single "Other" slice so the
    // donut and legend stay readable instead of showing a dozen 0–1% wedges.
    const TOP = 6
    if (mapped.length <= TOP) return mapped
    const top = mapped.slice(0, TOP)
    const rest = mapped.slice(TOP)
    return [
      ...top,
      {
        name: `Other (${rest.length})`,
        value: rest.reduce((sum, item) => sum + item.value, 0),
        percentage: Math.round(rest.reduce((sum, item) => sum + item.percentage, 0) * 10) / 10,
      },
    ]
  }, [data])
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
          <Legend verticalAlign="bottom" height={60} wrapperStyle={{ fontSize: '12px', paddingTop: '16px', color: 'var(--text-2)' }} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p id="job-type-mix-desc" className="sr-only">
        Pie chart showing job count distribution by employment type and remote status.
      </p>
    </>
  )
}
