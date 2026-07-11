import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi, type SystemHealthResponse } from '../../services/adminApi'

const POLL_INTERVAL_MS = 60_000

export default function AdminStatusBanner() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let cancelled = false

    function poll() {
      adminApi
        .getSystemHealth()
        .then((data) => {
          if (!cancelled) setHealth(data)
        })
        .catch(() => undefined)
    }

    poll()
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  if (!health || health.status === 'ok') return null

  const failingChecks = Object.entries(health.checks)
    .filter(([, check]) => check.status !== 'ok')
    .map(([name]) => name)

  const isUnhealthy = health.status === 'unhealthy'

  return (
    <div
      role="alert"
      className={`flex items-center justify-between gap-3 px-4 py-2 text-sm font-medium text-white ${
        isUnhealthy ? 'bg-red-600' : 'bg-amber-600'
      }`}
    >
      <span>
        {isUnhealthy ? 'System unhealthy' : 'System degraded'}
        {failingChecks.length > 0 && `: ${failingChecks.join(', ')}`}
      </span>
      <Link to="/admin/system" className="whitespace-nowrap underline hover:no-underline">
        View details
      </Link>
    </div>
  )
}
