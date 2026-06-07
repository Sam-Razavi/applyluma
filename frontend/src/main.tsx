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
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
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
