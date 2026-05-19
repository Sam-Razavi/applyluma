import type { Application } from '../types/application'

function cell(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  const str = String(value)
  return str.includes(',') || str.includes('"') || str.includes('\n')
    ? `"${str.replace(/"/g, '""')}"`
    : str
}

export function exportApplicationsToCsv(applications: Application[]) {
  const headers = [
    'Company',
    'Job Title',
    'Status',
    'Applied Date',
    'Location',
    'Remote Type',
    'Salary Min',
    'Salary Max',
    'Source',
    'Priority',
    'Job URL',
    'Notes',
    'Added',
  ]

  const rows = applications.map((a) => [
    cell(a.company_name),
    cell(a.job_title),
    cell(a.status),
    cell(a.applied_date),
    cell(a.location),
    cell(a.remote_type),
    cell(a.salary_min),
    cell(a.salary_max),
    cell(a.source),
    cell(a.priority),
    cell(a.job_url),
    cell(a.notes),
    cell(a.created_at.slice(0, 10)),
  ])

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `applyluma-applications-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
