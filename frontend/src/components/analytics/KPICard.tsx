import type { ElementType } from 'react'
import {
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  BriefcaseIcon,
  BuildingOffice2Icon,
  CurrencyDollarIcon,
  HomeIcon,
  MinusIcon,
} from '@heroicons/react/24/outline'
import { formatCurrency, formatNumber, formatPercentage } from '../../utils/formatters'

type KPIFormat = 'number' | 'currency' | 'percentage'
type KPIIcon = 'briefcase' | 'dollar' | 'building' | 'home' | 'trending-up'

interface KPICardProps {
  title: string
  value: number | null | undefined
  trend?: number | null
  format?: KPIFormat
  icon?: KPIIcon
  loading?: boolean
  error?: string | null
}

const ICONS: Record<KPIIcon, ElementType> = {
  briefcase: BriefcaseIcon,
  dollar: CurrencyDollarIcon,
  building: BuildingOffice2Icon,
  home: HomeIcon,
  'trending-up': ArrowTrendingUpIcon,
}

function formatValue(value: number, format: KPIFormat): string {
  if (format === 'currency') return formatCurrency(value)
  if (format === 'percentage') return formatPercentage(value)
  return formatNumber(value)
}

export default function KPICard({
  title,
  value,
  trend,
  format = 'number',
  icon = 'briefcase',
  loading = false,
  error = null,
}: KPICardProps) {
  const Icon = ICONS[icon]
  const TrendIcon = trend == null || trend === 0 ? MinusIcon : trend > 0 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon
  const trendColor = trend == null || trend === 0 ? 'text-gray-500' : trend > 0 ? 'text-success-600' : 'text-danger-600'

  if (loading) {
    return (
      <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="animate-pulse">
          <div className="mb-3 h-4 w-24 rounded bg-gray-200" />
          <div className="h-9 w-28 rounded bg-gray-200" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-danger-500/20 bg-danger-50 p-6 shadow-sm">
        <p className="text-sm font-medium text-danger-600">{title}</p>
        <p className="mt-2 text-sm text-danger-600">Failed to load</p>
      </div>
    )
  }

  return (
    <section
      className="group relative overflow-hidden rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-all duration-200 ease-in-out hover:border-primary-500 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
      aria-label={`${title} metric`}
      tabIndex={0}
    >
      <div className="absolute right-4 top-4 rounded-full bg-gray-50 p-2 transition-colors duration-200 group-hover:bg-primary-50">
        <Icon className="h-4 w-4 text-gray-400 transition-colors duration-200 group-hover:text-primary-600" aria-hidden="true" />
      </div>

      <div className="pr-10">
        <p className="text-sm font-medium text-gray-500">{title}</p>

        <div className="mt-2 flex items-end justify-between gap-3">
          <span className="break-words text-3xl font-bold text-gray-900">
            {value != null ? formatValue(value, format) : 'n/a'}
          </span>

          {trend != null && (
            <div className={`flex shrink-0 items-center gap-1 ${trendColor}`}>
              <TrendIcon className="h-4 w-4" aria-hidden="true" />
              <span className="text-sm font-semibold">
                {trend > 0 ? '+' : ''}
                {trend.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
