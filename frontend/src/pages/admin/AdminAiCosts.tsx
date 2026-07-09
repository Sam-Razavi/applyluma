import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import toast from 'react-hot-toast'
import {
  adminApi,
  type AiCostsBreakdown,
  type AiCostsDailyPoint,
  type AiCostsSummary,
} from '../../services/adminApi'

const PURPOSE_LABELS: Record<string, string> = {
  tailor: 'CV Tailor',
  tailor_verify: 'Tailor self-audit',
  tailor_compress: 'Tailor compress',
  cover_letter: 'Cover letters',
  cv_analysis: 'CV analysis',
  url_scrape: 'URL import',
}

function usd(value: number): string {
  return `$${value.toFixed(value >= 100 ? 0 : 2)}`
}

function StatCard({ label, cost, calls }: { label: string; cost: number; calls: number }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">{label}</p>
      <p className="mt-2 text-2xl font-bold text-fg">{usd(cost)}</p>
      <p className="mt-1 text-xs text-fg-subtle">{calls.toLocaleString()} API calls</p>
    </div>
  )
}

export default function AdminAiCosts() {
  const [summary, setSummary] = useState<AiCostsSummary | null>(null)
  const [daily, setDaily] = useState<AiCostsDailyPoint[]>([])
  const [breakdown, setBreakdown] = useState<AiCostsBreakdown | null>(null)
  const [loading, setLoading] = useState(true)
  const [budgetInput, setBudgetInput] = useState('')
  const [savingBudget, setSavingBudget] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, d, b] = await Promise.all([
        adminApi.getAiCostsSummary(),
        adminApi.getAiCostsDaily(30),
        adminApi.getAiCostsBreakdown(30),
      ])
      setSummary(s)
      setDaily(d)
      setBreakdown(b)
      setBudgetInput(s.budget.monthly_usd != null ? String(s.budget.monthly_usd) : '')
    } catch {
      toast.error('Could not load AI cost data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    document.title = 'AI Costs - ApplyLuma'
    void load()
  }, [load])

  async function saveBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = budgetInput.trim()
    const value = trimmed === '' ? null : Number(trimmed)
    if (value !== null && (!Number.isFinite(value) || value < 0)) {
      toast.error('Budget must be a positive number (or empty to disable)')
      return
    }
    setSavingBudget(true)
    try {
      const updated = await adminApi.updateAiBudget(value)
      setSummary(updated)
      toast.success(value === null ? 'Budget disabled' : 'Budget saved')
    } catch {
      toast.error('Could not save budget')
    } finally {
      setSavingBudget(false)
    }
  }

  const budget = summary?.budget
  const pct = budget?.pct_used ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">AI Costs</h1>
        <p className="mt-1 text-sm text-fg-subtle">
          OpenAI spend computed from per-call token usage. Tracking started when cost logging
          deployed — earlier usage is not included.
        </p>
      </div>

      {loading || !summary ? (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center text-sm text-fg-subtle">
          Loading cost data…
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Today" cost={summary.today.cost_usd} calls={summary.today.calls} />
            <StatCard
              label="Last 7 days"
              cost={summary.last_7_days.cost_usd}
              calls={summary.last_7_days.calls}
            />
            <StatCard
              label="Last 30 days"
              cost={summary.last_30_days.cost_usd}
              calls={summary.last_30_days.calls}
            />
            <StatCard
              label="All time"
              cost={summary.all_time.cost_usd}
              calls={summary.all_time.calls}
            />
          </div>

          {/* Budget */}
          <section className="rounded-2xl border border-line bg-surface p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
              Monthly budget
            </h2>
            <div className="mt-4 flex flex-wrap items-end gap-6">
              <form onSubmit={saveBudget} className="flex items-end gap-2">
                <div>
                  <label
                    htmlFor="ai-budget"
                    className="mb-1 block text-xs font-medium text-fg-muted"
                  >
                    Budget (USD / month)
                  </label>
                  <input
                    id="ai-budget"
                    type="number"
                    min={0}
                    step="0.01"
                    value={budgetInput}
                    onChange={(e) => setBudgetInput(e.target.value)}
                    placeholder="No budget set"
                    className="input w-40"
                  />
                </div>
                <button
                  type="submit"
                  disabled={savingBudget}
                  className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
                >
                  {savingBudget ? 'Saving…' : 'Save'}
                </button>
              </form>

              <div className="min-w-[220px] flex-1">
                {budget?.monthly_usd ? (
                  <>
                    <p className="text-sm text-fg-muted">
                      {usd(budget.month_to_date_usd)} of {usd(budget.monthly_usd)} used this month
                      {pct !== null && ` (${pct}%)`}
                    </p>
                    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-strong">
                      <div
                        className={`h-full rounded-full ${
                          pct !== null && pct >= 100
                            ? 'bg-chip-danger-fg'
                            : pct !== null && pct >= 80
                              ? 'bg-chip-warn-fg'
                              : 'bg-chip-success-fg'
                        }`}
                        style={{ width: `${Math.min(pct ?? 0, 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-fg-subtle">
                      Email alerts go out at 80% and 100% of budget.
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-fg-subtle">
                    No budget set — set one to get email alerts at 80% and 100% of monthly spend.
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* Daily chart */}
          <section className="rounded-2xl border border-line bg-surface p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
              Daily spend (30 days)
            </h2>
            <div className="mt-4">
              {daily.length === 0 ? (
                <p className="py-10 text-center text-sm text-fg-subtle">No usage recorded yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={daily} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--track)" />
                    <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 12 }} tickLine={false} />
                    <YAxis tick={{ fill: 'var(--text-3)', fontSize: 12 }} tickLine={false} />
                    <Tooltip formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
                    <Line type="monotone" dataKey="cost_usd" stroke="#6366f1" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* By purpose */}
            <section className="rounded-2xl border border-line bg-surface p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
                By feature (30 days)
              </h2>
              <div className="mt-4">
                {breakdown && breakdown.by_purpose.length > 0 ? (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={breakdown.by_purpose} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--track)" />
                      <XAxis
                        dataKey="key"
                        tickFormatter={(k: string) => PURPOSE_LABELS[k] ?? k}
                        tick={{ fill: 'var(--text-3)', fontSize: 11 }}
                        tickLine={false}
                      />
                      <YAxis tick={{ fill: 'var(--text-3)', fontSize: 12 }} tickLine={false} />
                      <Tooltip formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
                      <Bar dataKey="cost_usd" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="py-10 text-center text-sm text-fg-subtle">No usage recorded yet.</p>
                )}
              </div>
            </section>

            {/* Top users */}
            <section className="rounded-2xl border border-line bg-surface p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
                Top users by cost (30 days)
              </h2>
              <div className="mt-4 divide-y divide-line">
                {breakdown && breakdown.top_users.length > 0 ? (
                  breakdown.top_users.map((u) => (
                    <div
                      key={u.user_id ?? 'anonymous'}
                      className="flex items-center justify-between gap-3 py-2.5 text-sm"
                    >
                      <span className="truncate text-fg">{u.email ?? 'Anonymous / system'}</span>
                      <span className="flex-shrink-0 text-fg-muted">
                        {usd(u.cost_usd)} · {u.calls} calls
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="py-10 text-center text-sm text-fg-subtle">No usage recorded yet.</p>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
