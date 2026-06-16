import type { ConsentStatus } from '../../hooks/useCookieConsent'

interface Props {
  consent: ConsentStatus
  onAccept: () => void
  onDecline: () => void
}

export function CookieBanner({ consent, onAccept, onDecline }: Props) {
  if (consent !== null) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/10 bg-white/[0.04] shadow-lg">
      <div className="mx-auto flex max-w-7xl flex-col items-start gap-4 px-4 py-4 sm:flex-row sm:items-center">
        <p className="flex-1 text-sm text-white/55">
          We use optional analytics cookies (PostHog, Vercel) to understand how the app is
          used and improve it.{' '}
          <a href="/privacy" className="text-cyan-300 hover:underline">
            Learn more
          </a>
          .
        </p>
        <div className="flex shrink-0 gap-3">
          <button
            onClick={onDecline}
            className="rounded-lg bg-white/[0.04] px-4 py-2 text-sm font-medium text-white/55 transition-colors hover:bg-white/[0.08]"
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
