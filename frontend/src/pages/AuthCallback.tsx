import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, setToken } = useAuthStore()
  const processed = useRef(false)

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    const token = searchParams.get('token')
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
  }, [searchParams, login, setToken, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-white/[0.03]">
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
        <p className="text-sm text-white/50">Completing sign-in…</p>
      </div>
    </div>
  )
}
