import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../styles/analytics-colors'
import { formatNumber, titleCase } from '../../utils/formatters'
import type { ApplicationFunnelCount, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'

interface Props {
  data: ApplicationFunnelCount[]
}

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  wishlist: '#9ca3af',
  applied: '#3b82f6',
  phone_screen: '#f59e0b',
  interview: '#8b5cf6',
  offer: '#10b981',
  rejected: '#ef4444',
  withdrawn: '#64748b',
}

export default function FunnelChart({ data }: Props) {
  const counts = new Map(data.map((item) => [item.status, item.count]))
  const chartData = APPLICATION_STATUSES.map((status) => ({
    status,
    label: titleCase(status),
    count: counts.get(status) ?? 0,
  }))

  return (
    <div className="h-48 w-full md:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
        <XAxis dataKey="label" tick={CHART_AXIS_TICK} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
        <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
        <Tooltip
          formatter={(value) => [`${formatNumber(Number(value))} applications`, 'Count']}
          contentStyle={CHART_TOOLTIP_STYLE}
          cursor={{ fill: '#f9fafb' }}
        />
        <Bar dataKey="count" radius={[8, 8, 0, 0]}>
          {chartData.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLORS[entry.status]} />
          ))}
        </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
