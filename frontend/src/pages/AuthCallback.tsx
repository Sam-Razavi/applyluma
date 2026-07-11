import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

export default function AuthCallback() {
  const navigate = useNavigate()
  const { login, setToken } = useAuthStore()
  const processed = useRef(false)

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    // The token travels in the URL fragment (#token=...), not the query
    // string, so it's never sent to the server or logged. Read it directly
    // from location.hash (react-router's useSearchParams only sees the
    // query string) and strip it from the URL immediately so it doesn't
    // linger in the visible address bar any longer than necessary.
    const hashParams = new URLSearchParams(window.location.hash.slice(1))
    const token = hashParams.get('token')
    window.history.replaceState(null, '', window.location.pathname)

    if (!token) {
      navigate('/login?error=oauth_failed', { replace: true })
      return
    }

    // Store the token so the axios interceptor attaches it to /auth/me.
    setToken(token)
    authApi
      .me()
      .then((user) => {
        login(token, '', user)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        navigate('/login?error=oauth_failed', { replace: true })
      })
  }, [login, setToken, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="flex flex-col items-center gap-4">
        <svg
          className="h-10 w-10 animate-spin text-brand-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <p className="text-sm text-fg-muted">Completing sign-in…</p>
      </div>
    </div>
  )
}
