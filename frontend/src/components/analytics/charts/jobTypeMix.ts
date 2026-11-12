import type { JobTypeMixItem } from '../../../types'

export interface JobTypeSlice {
  name: string
  value: number
  percentage: number
}

const JOB_TYPE_LABELS: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  contract: 'Contract',
  internship: 'Internship',
  other: 'Other type',
  unknown: 'Type not stated',
}

const MAX_SLICES = 5

/** Chart slices from the API rows: readable names, largest first, and the
 *  long tail folded into one slice so the legend stays short. */
export function buildJobTypeSlices(data: JobTypeMixItem[]): JobTypeSlice[] {
  const slices = data
    .map((item) => ({
      name: `${JOB_TYPE_LABELS[item.job_type] ?? item.job_type}, ${item.remote_label === 'remote' ? 'remote' : 'on-site'}`,
      value: item.job_count,
      percentage: item.pct_of_total,
    }))
    .sort((a, b) => b.value - a.value)

  if (slices.length <= MAX_SLICES) return slices

  const rest = slices.slice(MAX_SLICES - 1)
  return [
    ...slices.slice(0, MAX_SLICES - 1),
    {
      name: `${rest.length} smaller groups`,
      value: rest.reduce((sum, item) => sum + item.value, 0),
      percentage: Math.round(rest.reduce((sum, item) => sum + item.percentage, 0) * 10) / 10,
    },
  ]
}
