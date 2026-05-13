import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores'

const DEFAULT_INACTIVITY_LIMIT_MS = 30 * 60 * 1000

const ACTIVITY_EVENTS = [
  'click',
  'keydown',
  'mousemove',
  'scroll',
  'touchstart',
  'focus',
] as const

export function useInactivityLogout(timeoutMs = DEFAULT_INACTIVITY_LIMIT_MS) {
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.token)
  const logout = useAuthStore((state) => state.logout)

  useEffect(() => {
    if (!token) return

    let timeoutId: ReturnType<typeof window.setTimeout>

    function handleInactive() {
      logout()
      navigate('/login?reason=inactive', { replace: true })
    }

    function resetTimer() {
      window.clearTimeout(timeoutId)
      timeoutId = window.setTimeout(handleInactive, timeoutMs)
    }

    resetTimer()
    ACTIVITY_EVENTS.forEach((eventName) => {
      window.addEventListener(eventName, resetTimer, { passive: true })
    })

    return () => {
      window.clearTimeout(timeoutId)
      ACTIVITY_EVENTS.forEach((eventName) => {
        window.removeEventListener(eventName, resetTimer)
      })
    }
  }, [logout, navigate, timeoutMs, token])
}
