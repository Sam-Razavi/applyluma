import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../styles/analytics-colors'
import { formatNumber, formatPeriod } from '../../utils/formatters'
import type { WeeklyApplicationCount } from '../../types/application'

interface Props {
  data: WeeklyApplicationCount[]
}

export default function ApplicationsOverTimeChart({ data }: Props) {
  const chartData = data.map((point) => ({
    week: point.week_start,
    count: point.count,
  }))

  return (
    <div className="h-48 w-full md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
        <XAxis
          dataKey="week"
          tickFormatter={formatPeriod}
          tick={CHART_AXIS_TICK}
          axisLine={{ stroke: '#e5e7eb' }}
          tickLine={false}
        />
        <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip
          labelFormatter={(label) => formatPeriod(String(label))}
          formatter={(value) => [`${formatNumber(Number(value))} applications`, 'Submitted']}
          contentStyle={CHART_TOOLTIP_STYLE}
          cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '5 5' }}
        />
        <Line
          type="monotone"
          dataKey="count"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 3, fill: '#6366f1' }}
          activeDot={{ r: 5, fill: '#6366f1' }}
        />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
