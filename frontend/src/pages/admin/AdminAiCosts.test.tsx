import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AdminAiCosts from './AdminAiCosts'

const { mockSummary, mockDaily, mockBreakdown, mockUpdateBudget } = vi.hoisted(() => ({
  mockSummary: vi.fn(),
  mockDaily: vi.fn(),
  mockBreakdown: vi.fn(),
  mockUpdateBudget: vi.fn(),
}))

vi.mock('../../services/adminApi', () => ({
  adminApi: {
    getAiCostsSummary: mockSummary,
    getAiCostsDaily: mockDaily,
    getAiCostsBreakdown: mockBreakdown,
    updateAiBudget: mockUpdateBudget,
  },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// recharts renders nothing measurable in jsdom; stub the ResponsiveContainer
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  }
})

const summary = {
  today: { cost_usd: 0.52, calls: 3, tokens: 12000 },
  last_7_days: { cost_usd: 4.2, calls: 30, tokens: 100000 },
  last_30_days: { cost_usd: 15.1, calls: 120, tokens: 400000 },
  all_time: { cost_usd: 42.0, calls: 400, tokens: 1200000 },
  budget: { monthly_usd: 50, month_to_date_usd: 12.5, pct_used: 25 },
}

const breakdown = {
  by_purpose: [{ key: 'tailor', cost_usd: 10, calls: 50, tokens: 300000 }],
  by_model: [{ key: 'gpt-4o', cost_usd: 10, calls: 50, tokens: 300000 }],
  top_users: [{ user_id: 'u1', email: 'top@user.com', cost_usd: 5.5, calls: 20 }],
}

describe('AdminAiCosts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSummary.mockResolvedValue(summary)
    mockDaily.mockResolvedValue([{ date: '2026-07-08', cost_usd: 1.25, calls: 10 }])
    mockBreakdown.mockResolvedValue(breakdown)
  })

  it('renders stat cards and budget usage', async () => {
    render(<AdminAiCosts />)
    expect(await screen.findByText('$42.00')).toBeInTheDocument()
    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText(/\$12\.50 of \$50\.00 used this month/)).toBeInTheDocument()
  })

  it('lists top users by cost', async () => {
    render(<AdminAiCosts />)
    expect(await screen.findByText('top@user.com')).toBeInTheDocument()
    expect(screen.getByText(/\$5\.50 · 20 calls/)).toBeInTheDocument()
  })

  it('saves the budget', async () => {
    mockUpdateBudget.mockResolvedValue({
      ...summary,
      budget: { monthly_usd: 75, month_to_date_usd: 12.5, pct_used: 16.7 },
    })
    render(<AdminAiCosts />)
    const input = await screen.findByLabelText('Budget (USD / month)')
    fireEvent.change(input, { target: { value: '75' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(mockUpdateBudget).toHaveBeenCalledWith(75))
  })

  it('rejects a negative budget without calling the API', async () => {
    render(<AdminAiCosts />)
    const input = await screen.findByLabelText('Budget (USD / month)')
    fireEvent.change(input, { target: { value: '-10' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(mockUpdateBudget).not.toHaveBeenCalled()
  })
})
