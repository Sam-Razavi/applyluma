import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  acceptEmailSuggestion,
  dismissEmailSuggestion,
  listEmailSuggestions,
  type EmailSuggestion,
} from '../../services/applicationsApi'
import { STATUS_META } from './statusMeta'

interface Props {
  /** Refresh the board after a status change lands. */
  onApplied: () => void
}

/**
 * Status changes proposed from forwarded email, awaiting confirmation.
 *
 * Nothing is applied until the user clicks. The sentence the classification
 * was based on is always shown: a suggestion whose reasoning is invisible is
 * one nobody can sensibly accept, and "we'll keep your CV on file" is exactly
 * the kind of message that reads as a rejection to a keyword matcher.
 */
export default function EmailSuggestions({ onApplied }: Props) {
  const [suggestions, setSuggestions] = useState<EmailSuggestion[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(() => {
    listEmailSuggestions()
      .then((data) => setSuggestions(data.items))
      // Silent: this is a secondary panel, and a failure here should never
      // bury the board behind an error.
      .catch(() => setSuggestions([]))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleAccept(suggestion: EmailSuggestion) {
    setBusyId(suggestion.id)
    try {
      await acceptEmailSuggestion(suggestion.id)
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id))
      toast.success(
        `${suggestion.company_name} moved to ${STATUS_META[suggestion.suggested_status].label}`,
      )
      onApplied()
    } catch {
      toast.error('Could not update the application')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDismiss(suggestion: EmailSuggestion) {
    setBusyId(suggestion.id)
    try {
      await dismissEmailSuggestion(suggestion.id)
      setSuggestions((current) => current.filter((item) => item.id !== suggestion.id))
    } catch {
      toast.error('Could not dismiss the suggestion')
    } finally {
      setBusyId(null)
    }
  }

  if (suggestions.length === 0) return null

  return (
    <section className="rounded-2xl border border-chip-warn bg-chip-warn/40 p-5">
      <h2 className="text-sm font-semibold text-fg">
        {suggestions.length === 1
          ? 'An email suggests a status change'
          : `${suggestions.length} emails suggest status changes`}
      </h2>
      <p className="mt-1 text-sm text-fg-muted">
        Nothing has been changed. Check each one before applying it.
      </p>

      <ul className="mt-4 space-y-3">
        {suggestions.map((suggestion) => (
          <li
            key={suggestion.id}
            className="rounded-xl border border-line bg-raised p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-semibold text-fg">{suggestion.company_name}</span>
              <span className="text-sm text-fg-subtle">{suggestion.job_title}</span>
            </div>

            <p className="mt-2 text-sm text-fg-muted">
              <span className="rounded-full bg-surface px-2 py-0.5 text-xs font-medium">
                {STATUS_META[suggestion.current_status].label}
              </span>
              <span aria-hidden="true"> → </span>
              <span className="rounded-full bg-chip-accent px-2 py-0.5 text-xs font-medium text-accent-text">
                {STATUS_META[suggestion.suggested_status].label}
              </span>
            </p>

            {suggestion.evidence && (
              <blockquote className="mt-3 border-l-2 border-line-strong pl-3 text-sm italic text-fg-muted">
                &ldquo;{suggestion.evidence}&rdquo;
              </blockquote>
            )}

            <p className="mt-2 text-xs text-fg-subtle">
              From {suggestion.from_address}
              {suggestion.subject ? ` — ${suggestion.subject}` : ''}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busyId === suggestion.id}
                onClick={() => void handleAccept(suggestion)}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                Update to {STATUS_META[suggestion.suggested_status].label}
              </button>
              <button
                type="button"
                disabled={busyId === suggestion.id}
                onClick={() => void handleDismiss(suggestion)}
                className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition hover:bg-surface-strong disabled:opacity-50"
              >
                Dismiss
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
