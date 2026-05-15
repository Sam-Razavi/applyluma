import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../styles/analytics-colors'
import { formatNumber, titleCase } from '../../utils/formatters'
import type { ApplicationSourceCount } from '../../types/application'

interface Props {
  data: ApplicationSourceCount[]
}

export default function SourceBreakdownChart({ data }: Props) {
  const chartData = data.map((item) => ({
    name: titleCase(item.source),
    value: item.count,
  }))
  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <div className="h-48 w-full md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="45%"
          innerRadius={54}
          outerRadius={96}
          paddingAngle={3}
          dataKey="value"
          nameKey="name"
          label={(entry) => `${Math.round((entry.value / Math.max(total, 1)) * 100)}%`}
          labelLine={false}
        >
          {chartData.map((entry, index) => (
            <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, _name, props) => [
            `${formatNumber(Number(value))} applications`,
            props.payload.name,
          ]}
          contentStyle={CHART_TOOLTIP_STYLE}
        />
        <Legend
          verticalAlign="bottom"
          height={48}
          wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
          iconType="circle"
        />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
