import { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatCompactCurrency, formatNumber, formatPercentage } from '../../../utils/formatters'
import type { IndustryBreakdown } from '../../../types'

interface Props {
  data: IndustryBreakdown[]
}

export default function IndustryBreakdownChart({ data }: Props) {
  const chartData = useMemo(() => {
    const topIndustries = data.slice(0, 7)
    const otherCount = data.slice(7).reduce((sum, industry) => sum + industry.job_count, 0)
    return [
      ...topIndustries.map((industry) => ({
        name: industry.industry,
        value: industry.job_count,
        percentage: industry.pct_of_total,
        salary: industry.avg_salary_min && industry.avg_salary_max ? (industry.avg_salary_min + industry.avg_salary_max) / 2 : null,
      })),
      ...(otherCount > 0 ? [{ name: 'Other', value: otherCount, percentage: 0, salary: null }] : []),
    ]
  }, [data])
  const totalJobs = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <>
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="45%"
            innerRadius={70}
            outerRadius={100}
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
              `${formatNumber(Number(value))} jobs (${formatPercentage(props.payload.percentage)}), ${formatCompactCurrency(props.payload.salary)} avg salary`,
              props.payload.name,
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
          <Legend verticalAlign="bottom" height={60} wrapperStyle={{ fontSize: '12px', paddingTop: '16px' }} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
      <p id="industry-breakdown-desc" className="sr-only">
        Donut chart showing job postings by derived industry segment.
      </p>
    </>
  )
}
