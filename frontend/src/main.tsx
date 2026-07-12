import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import * as Sentry from '@sentry/react'
import { initAnalytics } from './lib/analytics'
import './index.css'
import App from './App'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    // Exclude Sentry's own GlobalHandlers integration since we register explicit
    // window 'error'/'unhandledrejection' listeners below — keeps error reporting
    // documented in-repo instead of relying on undocumented default-integration
    // behavior, without double-reporting the same error.
    integrations: (defaults) => [
      ...defaults.filter((integration) => integration.name !== 'GlobalHandlers'),
      Sentry.browserTracingIntegration(),
    ],
    tracesSampleRate: 0.1,
  })

  window.addEventListener('error', (event) => {
    Sentry.captureException(event.error ?? event.message)
  })
  window.addEventListener('unhandledrejection', (event) => {
    Sentry.captureException(event.reason)
  })
}

// Only initialise analytics if the user previously accepted the cookie banner.
if (localStorage.getItem('cookie_consent') === 'accepted') {
  initAnalytics()
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { fontSize: '14px' },
        }}
      />
    </BrowserRouter>
  </StrictMode>,
)
