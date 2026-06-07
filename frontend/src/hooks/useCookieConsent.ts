import { useState } from 'react'
import { initAnalytics } from '../lib/analytics'

export type ConsentStatus = 'accepted' | 'declined' | null

const CONSENT_KEY = 'cookie_consent'

export function useCookieConsent() {
  const [consent, setConsent] = useState<ConsentStatus>(
    () => (localStorage.getItem(CONSENT_KEY) as ConsentStatus) ?? null,
  )

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, 'accepted')
    setConsent('accepted')
    initAnalytics()
  }

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, 'declined')
    setConsent('declined')
  }

  return { consent, accept, decline }
}
