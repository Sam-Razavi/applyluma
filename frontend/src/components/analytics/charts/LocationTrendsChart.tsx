import { useMemo } from 'react'
import { ResponsiveContainer, Tooltip, Treemap } from 'recharts'
import { CHART_TOOLTIP_STYLE, LOCATION_COLORS } from '../../../styles/analytics-colors'
import { formatCompactCurrency, formatNumber, formatPercentage } from '../../../utils/formatters'
import type { LocationTrend } from '../../../types'

interface Props {
  data: LocationTrend[]
}

interface TreemapTileProps {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  size?: number
  fill?: string
}

function TreemapTile({ x = 0, y = 0, width = 0, height = 0, name = '', size = 0, fill = '#4f46e5' }: TreemapTileProps) {
  if (width < 60 || height < 50) return null

  const shortName = name.length > 15 ? `${name.slice(0, 12)}...` : name

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#fff" strokeWidth={3} />
      {width > 80 && height > 60 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 8} textAnchor="middle" fill="#fff" fontSize={13} fontWeight={600}>
            {shortName}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" fill="#fff" fontSize={12} opacity={0.9}>
            {formatNumber(size)} jobs
          </text>
        </>
      )}
    </g>
  )
}

export default function LocationTrendsChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 12).map((location, index) => ({
        name: location.location,
        size: location.job_count,
        salary: location.avg_salary_midpoint,
        remote: location.remote_percentage,
        fill: LOCATION_COLORS[index % LOCATION_COLORS.length],
      })),
    [data],
  )

  return (
    <>
      <ResponsiveContainer width="100%" height={300}>
        <Treemap data={chartData} dataKey="size" nameKey="name" stroke="#fff" content={<TreemapTile />}>
          <Tooltip
            formatter={(value, _name, props) => [
              `${formatNumber(Number(value))} jobs, ${formatPercentage(props.payload.remote)} remote, ${formatCompactCurrency(props.payload.salary)} avg salary`,
              props.payload.name,
            ]}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
        </Treemap>
      </ResponsiveContainer>
      <p id="location-trends-desc" className="sr-only">
        Treemap showing geographic distribution of job postings.
      </p>
    </>
  )
}
