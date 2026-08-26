import { useCallback, useEffect, useState } from 'react'
import ErrorBanner from '../../components/ui/ErrorBanner'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminInboundEmailRow } from '../../services/adminApi'

const PAGE_SIZE = 25

type Filter = 'all' | 'matched' | 'unmatched'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'unmatched', label: 'Unmatched' },
  { key: 'matched', label: 'Matched' },
]

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

/** Green once the match was recorded, amber for near-misses worth reviewing. */
function confidenceClass(confidence: number, matched: boolean): string {
  if (matched) return 'bg-chip-success text-chip-success-fg'
  if (confidence > 0) return 'bg-chip-warn text-chip-warn-fg'
  return 'bg-chip-neutral text-chip-neutral-fg'
}

export default function AdminInboundEmails() {
  const [rows, setRows] = useState<AdminInboundEmailRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<Filter>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    adminApi
      .listInboundEmails({
        page,
        size: PAGE_SIZE,
        ...(filter === 'all' ? {} : { matched: filter === 'matched' }),
      })
      .then((data) => {
        setRows(data.items)
        setTotal(data.total)
      })
      .catch(() => setError('Failed to load inbound emails'))
      .finally(() => setLoading(false))
  }, [page, filter])

  useEffect(() => {
    document.title = 'Inbound Mail — ApplyLuma'
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <FadeIn>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-fg">Inbound Mail</h1>
          <p className="mt-1 text-sm text-fg-subtle">
            Forwarded email and what the matcher made of it. Nothing here changes an
            application&rsquo;s status &mdash; this view exists to judge matching accuracy
            against real mail.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => {
                setFilter(key)
                setPage(1)
              }}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                filter === key
                  ? 'bg-brand-600 text-white'
                  : 'bg-surface text-fg-muted hover:bg-surface-strong'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <ErrorBanner message={error} />}

        {loading ? (
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-track" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="rounded-2xl border border-line bg-surface px-6 py-16 text-center">
            <h2 className="text-sm font-semibold text-fg">No inbound mail yet</h2>
            <p className="mt-1 text-sm text-fg-subtle">
              Forwarded messages appear here once the MX record and webhook are live.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-line">
            <table className="min-w-full divide-y divide-line text-sm">
              <thead className="bg-surface">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">Received</th>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">From</th>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">Subject</th>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">Matched to</th>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">Confidence</th>
                  <th className="px-4 py-3 text-left font-semibold text-fg-muted">Why</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line bg-raised">
                {rows.map((row) => {
                  const matched = row.matched_application_id !== null
                  return (
                    <tr
                      key={row.id}
                      onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                      className="cursor-pointer align-top hover:bg-surface"
                    >
                      <td className="whitespace-nowrap px-4 py-3 text-fg-muted">
                        {formatDate(row.received_at ?? row.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-fg">{row.from_address}</div>
                        <div className="text-xs text-fg-subtle">{row.from_domain}</div>
                      </td>
                      <td className="max-w-xs px-4 py-3">
                        <div className="truncate text-fg" title={row.subject ?? ''}>
                          {row.subject ?? '—'}
                        </div>
                        {expanded === row.id && row.snippet && (
                          <p className="mt-2 whitespace-pre-wrap text-xs text-fg-subtle">
                            {row.snippet}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {matched ? (
                          <>
                            <div className="font-medium text-fg">
                              {row.matched_company_name ?? '—'}
                            </div>
                            <div className="text-xs text-fg-subtle">
                              {row.matched_job_title ?? ''}
                            </div>
                          </>
                        ) : (
                          <span className="rounded-full bg-chip-neutral px-2.5 py-0.5 text-xs font-medium text-chip-neutral-fg">
                            Unmatched
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${confidenceClass(
                            row.match_confidence,
                            matched,
                          )}`}
                        >
                          {row.match_confidence}
                        </span>
                        <div className="mt-1 text-xs text-fg-subtle">{row.match_method}</div>
                      </td>
                      <td className="max-w-sm px-4 py-3 text-xs text-fg-subtle">
                        {row.match_reason ?? '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition hover:bg-surface-strong disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-fg-subtle">
              Page {page} of {totalPages} &middot; {total} total
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition hover:bg-surface-strong disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </FadeIn>
  )
}
