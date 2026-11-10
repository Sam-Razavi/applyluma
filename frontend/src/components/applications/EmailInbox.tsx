import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDownIcon, EnvelopeIcon, TrashIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  deleteForwardedEmail,
  listForwardedEmails,
  type ForwardedEmail,
} from '../../services/emailForwardingApi'

const PAGE_SIZE = 20

type Filter = 'all' | 'matched' | 'unmatched'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'matched', label: 'Matched' },
  { id: 'unmatched', label: 'Not matched' },
]

const DETECTED: Record<string, { label: string; className: string }> = {
  rejection: { label: 'Rejection', className: 'bg-chip-danger text-chip-danger-fg' },
  interview: { label: 'Interview', className: 'bg-chip-accent text-accent-text' },
  offer: { label: 'Offer', className: 'bg-chip-success text-chip-success-fg' },
  acknowledged: { label: 'Application received', className: 'bg-surface-strong text-fg-muted' },
}

const STATE_LABEL: Record<ForwardedEmail['suggestion_state'], string | null> = {
  none: null,
  pending: 'Waiting for your decision',
  accepted: 'Status updated',
  dismissed: 'Dismissed',
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Every email the user forwarded, newest first: who it came from, what it
 * appears to say, which application it matched and what happened next.
 */
export default function EmailInbox() {
  const [filter, setFilter] = useState<Filter>('all')
  const [items, setItems] = useState<ForwardedEmail[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [openId, setOpenId] = useState<string | null>(null)

  const load = useCallback(
    async (skip: number) => {
      setLoading(true)
      try {
        const data = await listForwardedEmails({
          skip,
          limit: PAGE_SIZE,
          matched: filter === 'all' ? undefined : filter === 'matched',
        })
        setItems((current) => (skip === 0 ? data.items : [...current, ...data.items]))
        setTotal(data.total)
      } catch {
        toast.error('Could not load your emails')
      } finally {
        setLoading(false)
      }
    },
    [filter],
  )

  useEffect(() => {
    void load(0)
  }, [load])

  async function handleDelete(email: ForwardedEmail) {
    if (!window.confirm('Delete this email from ApplyLuma? Your own mailbox is not affected.')) return
    try {
      await deleteForwardedEmail(email.id)
      setItems((current) => current.filter((item) => item.id !== email.id))
      setTotal((t) => Math.max(0, t - 1))
      toast.success('Email deleted')
    } catch {
      toast.error('Could not delete the email')
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-fg">Forwarded emails</h2>
          <p className="text-sm text-fg-muted">
            What ApplyLuma received, what it spotted, and which application it belongs to.{' '}
            <Link to="/settings" className="text-accent-text hover:underline">
              Forwarding settings
            </Link>
          </p>
        </div>
        <div className="flex gap-1 self-start rounded-xl border border-line bg-surface p-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              aria-pressed={filter === f.id}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                filter === f.id ? 'bg-brand-600 text-white' : 'text-fg-subtle hover:bg-surface-strong'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {!loading && items.length === 0 ? (
        <div className="rounded-2xl border border-line bg-surface p-8 text-center">
          <EnvelopeIcon className="mx-auto h-8 w-8 text-fg-subtle" />
          <p className="mt-2 text-sm text-fg-muted">
            {filter === 'all'
              ? 'No forwarded emails yet.'
              : 'No emails in this view.'}{' '}
            <Link to="/settings" className="text-accent-text hover:underline">
              Set up forwarding
            </Link>
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          {items.map((email) => {
            const open = openId === email.id
            const detected = email.classification ? DETECTED[email.classification] : null
            const state = STATE_LABEL[email.suggestion_state]
            return (
              <li key={email.id}>
                <button
                  type="button"
                  onClick={() => setOpenId(open ? null : email.id)}
                  aria-expanded={open}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-strong"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm font-semibold text-fg">{email.from_address}</span>
                      <span className="shrink-0 text-xs text-fg-subtle">
                        {formatDate(email.received_at ?? email.created_at)}
                      </span>
                    </div>
                    <p className="truncate text-sm text-fg-muted">{email.subject || '(no subject)'}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
                      <span
                        className={`rounded-full px-2 py-0.5 font-medium ${
                          detected?.className ?? 'bg-surface-strong text-fg-subtle'
                        }`}
                      >
                        {detected?.label ?? 'Nothing detected'}
                      </span>
                      <span className="rounded-full border border-line px-2 py-0.5 text-fg-muted">
                        {email.company_name
                          ? `${email.company_name}${email.job_title ? ` — ${email.job_title}` : ''}`
                          : 'Not matched'}
                      </span>
                      {state && <span className="text-fg-subtle">· {state}</span>}
                    </div>
                  </div>
                  <ChevronDownIcon
                    className={`mt-1 h-4 w-4 shrink-0 text-fg-subtle transition ${open ? 'rotate-180' : ''}`}
                  />
                </button>

                {open && (
                  <div className="space-y-3 px-4 pb-4">
                    {email.evidence && (
                      <blockquote className="border-l-2 border-line-strong pl-3 text-sm italic text-fg-muted">
                        &ldquo;{email.evidence}&rdquo;
                      </blockquote>
                    )}
                    {email.snippet ? (
                      <p className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-raised p-3 text-sm text-fg-muted">
                        {email.snippet}
                      </p>
                    ) : (
                      <p className="text-sm text-fg-subtle">No text was kept for this email.</p>
                    )}
                    <p className="text-xs text-fg-subtle">
                      ApplyLuma keeps the first 2,000 characters of each email.
                    </p>
                    <button
                      type="button"
                      onClick={() => void handleDelete(email)}
                      className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-chip-danger-fg hover:bg-chip-danger"
                    >
                      <TrashIcon className="h-4 w-4" />
                      Delete
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {items.length < total && (
        <button
          type="button"
          disabled={loading}
          onClick={() => void load(items.length)}
          className="w-full rounded-xl border border-line bg-surface py-2.5 text-sm font-medium text-fg-muted hover:bg-surface-strong disabled:opacity-50"
        >
          {loading ? 'Loading…' : `Load more (${total - items.length} left)`}
        </button>
      )}
    </section>
  )
}
