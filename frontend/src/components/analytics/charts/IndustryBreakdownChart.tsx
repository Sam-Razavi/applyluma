import { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber, formatPercentage } from '../../../utils/formatters'
import { legendLabel } from './chartHelpers'
import type { IndustryBreakdown } from '../../../types'

// "Other" is a remainder, not a sector: a neutral grey keeps it from
// competing with the named slices.
const OTHER_COLOR = '#6b7280'

interface Props {
  data: IndustryBreakdown[]
}

export default function IndustryBreakdownChart({ data }: Props) {
  const chartData = useMemo(() => {
    // "Other" is already one of the sectors, so the tail joins it instead of
    // becoming a second slice with the same name.
    const named = data.filter((industry) => industry.industry !== 'Other')
    const top = named.slice(0, 6)
    const rest = [...named.slice(6), ...data.filter((industry) => industry.industry === 'Other')]
    const slices = top.map((industry) => ({
      name: industry.industry,
      value: industry.job_count,
      percentage: industry.pct_of_total,
    }))
    const otherCount = rest.reduce((sum, industry) => sum + industry.job_count, 0)
    if (otherCount > 0) {
      slices.push({
        name: 'Other',
        value: otherCount,
        percentage: Math.round(rest.reduce((sum, industry) => sum + industry.pct_of_total, 0) * 10) / 10,
      })
    }
    return slices
  }, [data])
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
            innerRadius="46%"
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
              <Cell key={entry.name} fill={entry.name === 'Other' ? OTHER_COLOR : CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs (${formatPercentage(props.payload.percentage)})`,
              props.payload.name,
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
          <Legend itemSorter={null} formatter={legendLabel} verticalAlign="bottom" height={100} wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p id="industry-breakdown-desc" className="sr-only">
        Donut chart showing job postings by derived industry segment.
      </p>
    </>
  )
}
