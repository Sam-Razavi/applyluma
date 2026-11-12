import { describe, expect, it } from 'vitest'
import { buildJobTypeSlices } from './jobTypeMix'
import type { JobTypeMixItem } from '../../../types'

const item = (job_type: string, remote_label: string, job_count: number, pct_of_total = 0): JobTypeMixItem => ({
  job_type,
  remote_label,
  job_count,
  pct_of_total,
  avg_salary_min: null,
  avg_salary_max: null,
})

describe('buildJobTypeSlices', () => {
  it('gives every slice a readable, unique name, largest first', () => {
    const slices = buildJobTypeSlices([
      item('part_time', 'on-site', 50),
      item('full_time', 'on-site', 2000),
      item('unknown', 'remote', 90),
    ])

    expect(slices.map((s) => s.name)).toEqual([
      'Full-time, on-site',
      'Type not stated, remote',
      'Part-time, on-site',
    ])
  })

  it('folds the tail into one slice with its combined count and share', () => {
    const slices = buildJobTypeSlices([
      item('full_time', 'on-site', 100, 50),
      item('full_time', 'remote', 40, 20),
      item('part_time', 'on-site', 30, 15),
      item('contract', 'remote', 12, 6),
      item('unknown', 'remote', 8, 4),
      item('internship', 'on-site', 6, 3),
      item('other', 'on-site', 4, 2),
    ])

    expect(slices).toHaveLength(5)
    expect(slices[4]).toEqual({ name: '3 smaller groups', value: 18, percentage: 9 })
    expect(new Set(slices.map((s) => s.name)).size).toBe(5)
  })
})
