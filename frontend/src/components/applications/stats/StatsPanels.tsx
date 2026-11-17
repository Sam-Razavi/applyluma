import { Link } from 'react-router-dom'
import type {
  ApplicationSalaryBucketCount,
  InsightDailyCount,
  InsightCvPerformance,
  InsightLabelCount,
  InsightSourcePerformance,
  InsightStageReach,
  InsightUpcomingItem,
} from '../../../types/application'
import { titleCase } from '../../../utils/formatters'
import { pct } from './statsSummary'

const STAGE_LABELS: Record<InsightStageReach['stage'], string> = {
  applied: 'Applied',
  phone_screen: 'Phone screen',
  interview: 'Interview',
  offer: 'Offer',
}

/** One headline number with a plain-language hint underneath. */
export function StatTile({
  label,
  value,
  hint,
  trend,
  tone = 'default',
}: {
  label: string
  value: string
  hint?: string
  trend?: number | null
  tone?: 'default' | 'warn'
}) {
  const trendColor = trend == null || trend === 0 ? 'text-fg-subtle' : trend > 0 ? 'text-success-600' : 'text-danger-600'
  return (
    <section
      aria-label={label}
      className={`rounded-lg border bg-surface p-4 shadow-sm ${
        tone === 'warn' ? 'border-chip-warn-fg/30' : 'border-line'
      }`}
    >
      <p className="text-xs font-medium text-fg-subtle">{label}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        <span className="text-2xl font-bold text-fg">{value}</span>
        {trend != null && (
          <span className={`shrink-0 text-xs font-semibold ${trendColor}`}>
            {trend > 0 ? '+' : ''}
            {trend.toFixed(0)}%
          </span>
        )}
      </div>
      {hint && <p className="mt-1 text-xs text-fg-muted">{hint}</p>}
    </section>
  )
}

/** Horizontal bars, one row per label. Width is relative to the largest value. */
export function BarList({
  rows,
  emptyText,
  unit = '',
}: {
  rows: { label: string; value: number; note?: string }[]
  emptyText: string
  unit?: string
}) {
  if (rows.length === 0 || rows.every((r) => r.value === 0)) {
    return <p className="py-6 text-center text-sm text-fg-muted">{emptyText}</p>
  }
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <li key={row.label}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-fg">{row.label}</span>
            <span className="shrink-0 font-medium text-fg">
              {row.value}
              {unit}
              {row.note && <span className="ml-1.5 text-xs font-normal text-fg-subtle">{row.note}</span>}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-track">
            <div
              className="h-full rounded-full"
              style={{ width: `${(row.value / max) * 100}%`, background: 'var(--accent)' }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

/** How far applications got, as a share of everything sent. */
export function StageProgress({ stages, submitted }: { stages: InsightStageReach[]; submitted: number }) {
  return (
    <div>
      <ul className="space-y-3">
        {stages.map((stage, index) => (
          <li key={stage.stage}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="text-fg">{STAGE_LABELS[stage.stage]}</span>
              <span className="font-medium text-fg">
                {stage.count}
                <span className="ml-1.5 text-xs font-normal text-fg-subtle">{pct(stage.rate)}</span>
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-track">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(stage.rate * 100, stage.count > 0 ? 3 : 0)}%`,
                  background: 'var(--accent)',
                  opacity: 1 - index * 0.18,
                }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-fg-muted">
        Out of {submitted} sent. Each bar counts every application that reached that stage, even if it was
        later rejected.
      </p>
    </div>
  )
}

/** Applications sent on each of the last 7 days, today on the right. */
export function DailyBars({ days }: { days: InsightDailyCount[] }) {
  const total = days.reduce((sum, d) => sum + d.count, 0)
  const max = Math.max(...days.map((d) => d.count), 1)
  const label = (iso: string, index: number) => {
    // Parse as a plain calendar date: the server already chose the day.
    const [y, m, d] = iso.split('-').map(Number)
    const date = new Date(y, m - 1, d)
    return {
      weekday: index === days.length - 1 ? 'Today' : date.toLocaleDateString('en-US', { weekday: 'short' }),
      day: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }
  }
  return (
    <div>
      <div className="flex h-40 gap-2" role="img" aria-label="Applications sent per day, last 7 days">
        {days.map((day, index) => {
          const text = label(day.date, index)
          const isToday = index === days.length - 1
          return (
            <div key={day.date} className="flex h-full flex-1 flex-col items-center gap-1">
              <span className={`text-sm font-semibold ${day.count > 0 ? 'text-fg' : 'text-fg-subtle'}`}>
                {day.count}
              </span>
              <div className="flex w-full flex-1 items-end">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(day.count / max) * 100}%`,
                    minHeight: day.count > 0 ? 6 : 2,
                    background: isToday ? 'var(--accent)' : day.count > 0 ? 'var(--accent-text)' : 'var(--track)',
                    opacity: isToday || day.count === 0 ? 1 : 0.55,
                  }}
                />
              </div>
              <span className={`text-xs ${isToday ? 'font-semibold text-fg' : 'text-fg-subtle'}`}>
                {text.weekday}
              </span>
              <span className="hidden text-[10px] text-fg-subtle sm:block">{text.day}</span>
            </div>
          )
        })}
      </div>
      <p className="mt-3 text-xs text-fg-muted">
        {total === 0
          ? 'Nothing sent in the last 7 days.'
          : `${total} application${total === 1 ? '' : 's'} sent in the last 7 days (${(total / 7).toFixed(1)} a day on average).`}
      </p>
    </div>
  )
}

/** Which weekday applications were sent on. */
export function WeekdayBars({ days }: { days: InsightLabelCount[] }) {
  const max = Math.max(...days.map((d) => d.count), 1)
  const total = days.reduce((sum, d) => sum + d.count, 0)
  if (total === 0) {
    return <p className="py-6 text-center text-sm text-fg-muted">Send a few applications to see your pattern.</p>
  }
  const best = days.reduce((a, b) => (b.count > a.count ? b : a))
  return (
    <div>
      <div className="flex h-36 gap-2" role="img" aria-label="Applications sent per weekday">
        {days.map((day) => (
          <div key={day.label} className="flex h-full flex-1 flex-col items-center gap-1">
            <span className="text-xs text-fg-muted">{day.count}</span>
            <div className="flex w-full flex-1 items-end">
              <div
                className="w-full rounded-t"
                style={{
                  height: `${(day.count / max) * 100}%`,
                  minHeight: day.count > 0 ? 4 : 2,
                  background: day.label === best.label ? 'var(--accent)' : 'var(--accent-muted)',
                }}
              />
            </div>
            <span className="text-xs text-fg-subtle">{day.label}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-fg-muted">You send the most applications on {best.label}.</p>
    </div>
  )
}

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-xs text-fg-subtle">
            {headers.map((h, i) => (
              <th key={h} className={`pb-2 font-medium ${i > 0 ? 'text-right' : ''}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  )
}

export function SourceTable({ rows }: { rows: InsightSourcePerformance[] }) {
  if (rows.length === 0) return <p className="py-6 text-center text-sm text-fg-muted">No sources yet.</p>
  return (
    <Table headers={['Source', 'Sent', 'Replies', 'Reply rate']}>
      {rows.map((row) => (
        <tr key={row.source}>
          <td className="py-2 pr-3 text-fg">{titleCase(row.source)}</td>
          <td className="py-2 text-right text-fg">{row.applications}</td>
          <td className="py-2 text-right text-fg">{row.responses}</td>
          <td className="py-2 text-right font-medium text-fg">{pct(row.response_rate)}</td>
        </tr>
      ))}
    </Table>
  )
}

export function CvTable({ rows }: { rows: InsightCvPerformance[] }) {
  if (rows.length === 0) return <p className="py-6 text-center text-sm text-fg-muted">No applications yet.</p>
  return (
    <div>
      <Table headers={['CV', 'Sent', 'Replies', 'Reply rate']}>
        {rows.map((row) => (
          <tr key={row.cv_id ?? 'none'}>
            <td className="max-w-[10rem] truncate py-2 pr-3 text-fg">{row.title}</td>
            <td className="py-2 text-right text-fg">{row.applications}</td>
            <td className="py-2 text-right text-fg">{row.responses}</td>
            <td className="py-2 text-right font-medium text-fg">{pct(row.response_rate)}</td>
          </tr>
        ))}
      </Table>
      <p className="mt-3 text-xs text-fg-muted">Small samples are noisy: a few applications prove little.</p>
    </div>
  )
}

export function UpcomingList({ items }: { items: InsightUpcomingItem[] }) {
  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-fg-muted">
        No interviews or wishlist deadlines in the next 2 weeks.
      </p>
    )
  }
  return (
    <ul className="divide-y divide-line">
      {items.map((item) => (
        <li key={`${item.application_id}-${item.kind}`} className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <Link to="/applications" className="block truncate text-sm font-medium text-fg hover:underline">
              {item.company_name}
            </Link>
            <p className="truncate text-xs text-fg-muted">{item.job_title}</p>
          </div>
          <div className="shrink-0 text-right">
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                item.kind === 'interview' ? 'bg-chip-accent text-chip-accent-fg' : 'bg-chip-warn text-chip-warn-fg'
              }`}
            >
              {item.kind === 'interview' ? 'Interview' : 'Apply by'}
            </span>
            <p className="mt-0.5 text-xs text-fg-muted">
              {item.days_away === 0 ? 'Today' : item.days_away === 1 ? 'Tomorrow' : `In ${item.days_away} days`}
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}

const kilo = (value: number) => `${Math.round(value / 1000)}k`

export function SalarySummary({
  buckets,
  median,
  min,
  max,
  sample,
}: {
  buckets: ApplicationSalaryBucketCount[]
  median: number | null
  min: number | null
  max: number | null
  sample: number
}) {
  if (sample === 0) {
    return (
      <p className="py-6 text-center text-sm text-fg-muted">
        Add a salary range to your applications to compare offers here.
      </p>
    )
  }
  return (
    <div>
      <p className="mb-4 text-sm text-fg-muted">
        Typical pay across {sample} application{sample === 1 ? '' : 's'} with a salary:{' '}
        <span className="font-semibold text-fg">{median != null ? kilo(median) : 'n/a'}</span>
        {min != null && max != null && min !== max && (
          <span>
            {' '}
            (from {kilo(min)} to {kilo(max)})
          </span>
        )}
        .
      </p>
      <BarList rows={buckets.map((b) => ({ label: b.bucket, value: b.count }))} emptyText="No salary data." />
    </div>
  )
}
