import type { ConsentStatus } from '../../hooks/useCookieConsent'

interface Props {
  consent: ConsentStatus
  onAccept: () => void
  onDecline: () => void
}

export function CookieBanner({ consent, onAccept, onDecline }: Props) {
  if (consent !== null) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-line bg-surface shadow-lg">
      <div className="mx-auto flex max-w-7xl flex-col items-start gap-4 px-4 py-4 sm:flex-row sm:items-center">
        <p className="flex-1 text-sm text-fg-muted">
          We use optional analytics cookies (PostHog, Vercel) to understand how the app is
          used and improve it.{' '}
          <a href="/privacy" className="text-accent-text hover:underline">
            Learn more
          </a>
          .
        </p>
        <div className="flex shrink-0 gap-3">
          <button
            onClick={onDecline}
            className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
          >
            Decline optional
          </button>
          <button
            onClick={onAccept}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
          >
            Accept all
          </button>
        </div>
      </div>
    </div>
  )
}
