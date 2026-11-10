import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowPathIcon, ClipboardDocumentIcon, EnvelopeIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  getEmailForwarding,
  rotateEmailForwarding,
  type EmailForwardingStatus,
} from '../../services/emailForwardingApi'

// Words that appear in almost every application reply, in English and
// Swedish. Used for a mail filter, so only job mail is forwarded.
export const FILTER_WORDS =
  'application OR applying OR applied OR interview OR candidate OR ansökan OR intervju OR tjänsten OR kandidat'

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function copy(text: string, what: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(`${what} copied`)
  } catch {
    toast.error('Could not copy. Select the text and copy it yourself.')
  }
}

/**
 * The user's forwarding address and how to set up forwarding. Rendered only
 * when the server says the feature is enabled for this user.
 */
export default function EmailForwardingCard() {
  const [status, setStatus] = useState<EmailForwardingStatus | null>(null)
  const [rotating, setRotating] = useState(false)

  useEffect(() => {
    let active = true
    const load = () =>
      getEmailForwarding()
        .then((data) => active && setStatus(data))
        .catch(() => active && setStatus(null))
    void load()
    // Gmail's confirmation code arrives a few seconds after the user adds the
    // address, so check again while the page is open.
    const timer = window.setInterval(() => void load(), 15000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  async function handleRotate() {
    if (!window.confirm('Get a new address? The current one stops working, so update any forwarding rule that uses it.')) {
      return
    }
    setRotating(true)
    try {
      setStatus(await rotateEmailForwarding())
      toast.success('New forwarding address created')
    } catch {
      toast.error('Could not create a new address')
    } finally {
      setRotating(false)
    }
  }

  if (!status?.enabled || !status.address) return null
  const { address, gmail_confirmation: confirmation } = status

  return (
    <section className="rounded-2xl border border-line bg-surface p-6" aria-labelledby="email-forwarding-title">
      <div className="mb-4 flex items-center gap-2">
        <EnvelopeIcon className="h-5 w-5 text-accent-text" />
        <h2 id="email-forwarding-title" className="text-sm font-semibold text-fg">
          Email forwarding
        </h2>
      </div>

      <p className="text-sm text-fg-muted">
        Forward recruiter emails to this address. ApplyLuma spots rejections, interviews and
        offers and asks you before changing an application.
      </p>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <code className="min-w-0 flex-1 break-all rounded-lg border border-line bg-raised px-3 py-2 text-sm text-fg">
          {address}
        </code>
        <button
          type="button"
          onClick={() => void copy(address, 'Address')}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          <ClipboardDocumentIcon className="h-4 w-4" />
          Copy
        </button>
      </div>

      <p className="mt-2 text-xs text-fg-subtle">
        {status.emails_received === 0
          ? 'No emails received yet.'
          : `${status.emails_received} ${status.emails_received === 1 ? 'email' : 'emails'} received` +
            (status.last_received_at ? `, latest ${formatDate(status.last_received_at)}.` : '.')}
      </p>

      {confirmation && (
        <div className="mt-4 rounded-xl border border-chip-warn bg-chip-warn px-4 py-3" role="status">
          <p className="text-sm font-medium text-chip-warn-fg">Gmail wants you to confirm forwarding</p>
          {confirmation.code && (
            <p className="mt-1 text-sm text-fg-muted">
              Confirmation code: <span className="font-mono font-semibold text-fg">{confirmation.code}</span>
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {confirmation.link && (
              <a
                href={confirmation.link}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Confirm forwarding
              </a>
            )}
            {confirmation.code && (
              <button
                type="button"
                onClick={() => void copy(confirmation.code ?? '', 'Code')}
                className="rounded-lg bg-surface-strong px-3 py-1.5 text-sm font-medium text-fg-muted"
              >
                Copy code
              </button>
            )}
          </div>
        </div>
      )}

      <div className="mt-5 space-y-2">
        <details className="rounded-xl border border-line px-4 py-3">
          <summary className="cursor-pointer text-sm font-medium text-fg">Set up in Gmail</summary>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-fg-muted">
            <li>
              On a computer (the Gmail phone app cannot do this), open Gmail, click the gear,
              then <strong>See all settings</strong> → <strong>Forwarding and POP/IMAP</strong>.
            </li>
            <li>
              Click <strong>Add a forwarding address</strong>, paste the address above, then{' '}
              <strong>Next</strong> → <strong>Proceed</strong> → <strong>OK</strong>.
            </li>
            <li>
              Gmail sends a confirmation code to ApplyLuma. Within a minute it appears on this
              page: click <strong>Confirm forwarding</strong>.
            </li>
            <li>
              Leave forwarding itself <strong>disabled</strong>, so not all your mail is sent.
              Instead, in the Gmail search bar click the filter icon, paste this into{' '}
              <strong>Has the words</strong>:
              <span className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center">
                <code className="min-w-0 flex-1 break-all rounded bg-raised px-2 py-1 text-xs">{FILTER_WORDS}</code>
                <button
                  type="button"
                  onClick={() => void copy(FILTER_WORDS, 'Filter words')}
                  className="self-start rounded bg-surface-strong px-2 py-1 text-xs font-medium"
                >
                  Copy
                </button>
              </span>
            </li>
            <li>
              Click <strong>Create filter</strong>, tick <strong>Forward it to</strong>, choose
              your ApplyLuma address, and click <strong>Create filter</strong>.
            </li>
          </ol>
        </details>

        <details className="rounded-xl border border-line px-4 py-3">
          <summary className="cursor-pointer text-sm font-medium text-fg">Set up in Outlook or Hotmail</summary>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-fg-muted">
            <li>
              In Outlook on the web, open <strong>Settings</strong> → <strong>Mail</strong> →{' '}
              <strong>Rules</strong> → <strong>Add new rule</strong>.
            </li>
            <li>
              Name it ApplyLuma. Condition: <strong>Subject or body includes</strong>, and add
              words such as application, interview, ansökan, intervju.
            </li>
            <li>
              Action: <strong>Forward to</strong>, paste the address above, and save.
            </li>
          </ol>
        </details>

        <details className="rounded-xl border border-line px-4 py-3">
          <summary className="cursor-pointer text-sm font-medium text-fg">Forward by hand</summary>
          <p className="mt-3 text-sm text-fg-muted">
            Forward any recruiter email to the address above, from any mail app. ApplyLuma reads
            the original sender from the forwarded message.
          </p>
        </details>
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-fg-subtle">
          We keep the sender, subject and the first 2,000 characters of each email, never
          attachments. See the <Link to="/privacy" className="text-accent-text hover:underline">privacy policy</Link>.
        </p>
        <button
          type="button"
          disabled={rotating}
          onClick={() => void handleRotate()}
          className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg bg-surface-strong px-3 py-2 text-xs font-medium text-fg-muted disabled:opacity-50"
        >
          {rotating && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
          Get a new address
        </button>
      </div>
    </section>
  )
}
