import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import AdminDatabase from './AdminDatabase'

const { mockGetDatabaseStats } = vi.hoisted(() => ({
  mockGetDatabaseStats: vi.fn(),
}))

vi.mock('../../services/adminApi', () => ({
  adminApi: { getDatabaseStats: mockGetDatabaseStats },
}))

const stats = {
  database_size_bytes: 1_500_000_000,
  generated_at: '2026-07-11T00:00:00Z',
  tables: [
    {
      table_name: 'raw_job_postings',
      approx_row_count: 810,
      total_bytes: 9_000_000,
      rows_7d: 70,
      rows_30d: 300,
    },
    {
      table_name: 'alembic_version',
      approx_row_count: 1,
      total_bytes: 8192,
      rows_7d: null,
      rows_30d: null,
    },
  ],
}

describe('AdminDatabase', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDatabaseStats.mockResolvedValue(stats)
  })

  it('renders total database size and per-table rows', async () => {
    render(<AdminDatabase />)

    expect(await screen.findByText('1.4 GB')).toBeInTheDocument()
    expect(screen.getByText('raw_job_postings')).toBeInTheDocument()
    expect(screen.getByText('810')).toBeInTheDocument()
    expect(screen.getByText('+70')).toBeInTheDocument()
    expect(screen.getByText('+300')).toBeInTheDocument()
  })

  it('shows a dash for tables with no growth data', async () => {
    render(<AdminDatabase />)

    await screen.findByText('alembic_version')
    const row = screen.getByText('alembic_version').closest('tr') as HTMLElement
    expect(row).toHaveTextContent('—')
  })

  it('shows an error message when the request fails', async () => {
    mockGetDatabaseStats.mockRejectedValue(new Error('boom'))
    render(<AdminDatabase />)

    expect(await screen.findByText('Failed to load database stats')).toBeInTheDocument()
  })
})
