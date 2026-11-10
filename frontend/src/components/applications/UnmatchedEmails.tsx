import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  assignUnmatchedEmail,
  dismissUnmatchedEmail,
  listUnmatchedEmails,
  type UnmatchedEmail,
} from '../../services/applicationsApi'
import type { Application } from '../../types/application'
import { STATUS_META } from './statusMeta'

interface Props {
  applications: Application[]
  /** Refresh the board after a status change lands. */
  onApplied: () => void
}

/**
 * Forwarded emails that read as a rejection, interview or offer but could not
 * be tied to an application (often a recruiting system's no-reply address).
 * One choice from the list attaches the email and applies its status.
 */
export default function UnmatchedEmails({ applications, onApplied }: Props) {
  const [emails, setEmails] = useState<UnmatchedEmail[]>([])
  const [choice, setChoice] = useState<Record<string, string>>({})
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(() => {
    listUnmatchedEmails()
      .then((data) => setEmails(data.items))
      // Silent, like the suggestions panel: never bury the board in errors.
      .catch(() => setEmails([]))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function remove(id: string) {
    setEmails((current) => current.filter((item) => item.id !== id))
  }

  async function handleAssign(email: UnmatchedEmail) {
    const applicationId = choice[email.id]
    if (!applicationId) return
    setBusyId(email.id)
    try {
      const updated = await assignUnmatchedEmail(email.id, applicationId)
      remove(email.id)
      toast.success(`${updated.company_name} moved to ${STATUS_META[email.suggested_status].label}`)
      onApplied()
    } catch {
      toast.error('Could not update the application')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDismiss(email: UnmatchedEmail) {
    setBusyId(email.id)
    try {
      await dismissUnmatchedEmail(email.id)
      remove(email.id)
    } catch {
      toast.error('Could not dismiss the email')
    } finally {
      setBusyId(null)
    }
  }

  if (emails.length === 0 || applications.length === 0) return null

  const sorted = [...applications].sort((a, b) => a.company_name.localeCompare(b.company_name))

  return (
    <section className="rounded-2xl border border-line bg-surface p-5">
      <h2 className="text-sm font-semibold text-fg">
        {emails.length === 1
          ? 'Which application is this email about?'
          : `${emails.length} emails need an application`}
      </h2>
      <p className="mt-1 text-sm text-fg-muted">
        We could not tell which job these are about. Pick one and its status is updated.
      </p>

      <ul className="mt-4 space-y-3">
        {emails.map((email) => {
          const label = STATUS_META[email.suggested_status].label
          const selectId = `unmatched-${email.id}`
          return (
            <li key={email.id} className="rounded-xl border border-line bg-raised p-4 shadow-sm">
              <p className="text-sm text-fg">
                Looks like{' '}
                <span className="rounded-full bg-chip-accent px-2 py-0.5 text-xs font-medium text-accent-text">
                  {label}
                </span>
              </p>
              {email.evidence && (
                <blockquote className="mt-3 border-l-2 border-line-strong pl-3 text-sm italic text-fg-muted">
                  &ldquo;{email.evidence}&rdquo;
                </blockquote>
              )}
              <p className="mt-2 text-xs text-fg-subtle">
                From {email.from_address}
                {email.subject ? ` — ${email.subject}` : ''}
              </p>

              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
                <label htmlFor={selectId} className="sr-only">
                  Application
                </label>
                <select
                  id={selectId}
                  value={choice[email.id] ?? ''}
                  onChange={(e) => setChoice((c) => ({ ...c, [email.id]: e.target.value }))}
                  className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="">Choose the application…</option>
                  {sorted.map((application) => (
                    <option key={application.id} value={application.id}>
                      {application.company_name} — {application.job_title}
                    </option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busyId === email.id || !choice[email.id]}
                    onClick={() => void handleAssign(email)}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
                  >
                    Update to {label}
                  </button>
                  <button
                    type="button"
                    disabled={busyId === email.id}
                    onClick={() => void handleDismiss(email)}
                    className="rounded-lg bg-surface-strong px-4 py-2 text-sm font-medium text-fg-muted transition hover:bg-surface disabled:opacity-50"
                  >
                    Not a job email
                  </button>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
