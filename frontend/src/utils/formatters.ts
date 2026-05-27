export const formatCurrency = (value: number | null | undefined): string => {
  if (value == null) return 'n/a'

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export const formatCompactCurrency = (value: number | null | undefined): string => {
  if (value == null) return 'n/a'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}k`
  return `$${value}`
}

export const formatPercentage = (
  value: number | null | undefined,
  decimals = 1,
): string => {
  if (value == null) return '0%'
  return `${value.toFixed(decimals)}%`
}

export const formatNumber = (value: number | null | undefined): string => {
  if (value == null) return '0'
  return new Intl.NumberFormat('en-US').format(value)
}

export const formatDate = (date: string): string => {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(date))
}

export const formatShortDate = (date: string): string => {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(date))
}

export const titleCase = (value: string): string => {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

export const formatPeriod = (period: string): string => {
  if (/^\d{4}-\d{2}-\d{2}$/.test(period)) return formatShortDate(period)
  return period
}
