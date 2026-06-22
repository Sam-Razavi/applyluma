import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { EnvelopeIcon, XMarkIcon } from '@heroicons/react/24/outline'
import Sidebar from './Sidebar'
import MobileNav from './MobileNav'
import { useInactivityLogout } from '../../hooks/useInactivityLogout'
import { useNotificationsStore } from '../../stores/notifications'
import { useAuthStore } from '../../stores'
import { authApi } from '../../services/authApi'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/applications': 'Applications',
  '/discover': 'Discover',
  '/saved-jobs': 'My Jobs',
  '/settings': 'Settings',
  '/cv': 'My CVs',
  '/jobs': 'My Jobs',
}

export default function AppLayout() {
  useInactivityLogout()
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [resending, setResending] = useState(false)
  const location = useLocation()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const user = useAuthStore((s) => s.user)
  const showVerifyBanner = !!user && !user.is_verified && !bannerDismissed

  async function handleResend() {
    setResending(true)
    try {
      await authApi.resendVerification()
      setBannerDismissed(true)
    } catch {
      // silently ignore
    } finally {
      setResending(false)
    }
  }

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  useEffect(() => {
    const base = PAGE_TITLES[location.pathname] ?? 'ApplyLuma'
    const title = `${base} | ApplyLuma`
    document.title = unreadCount > 0 ? `(${unreadCount}) ${title}` : title
  }, [location.pathname, unreadCount])

  return (
    <div
      className="flex min-h-dvh"
      style={{
        background: 'linear-gradient(140deg, #080E12 0%, #0A1118 55%, #070C10 100%)',
      }}
    >
      <Sidebar />

      <main className="flex-1 pb-24 pt-4 md:ml-[224px] md:pb-8 md:pt-0">
        {showVerifyBanner && (
          <div
            className="mx-4 mt-2 flex items-center justify-between gap-3 rounded-xl px-4 py-2.5 text-sm md:mx-8"
            style={{
              background: 'rgba(8,145,178,0.10)',
              border: '1px solid rgba(8,145,178,0.25)',
              color: 'var(--accent-text)',
            }}
          >
            <div className="flex items-center gap-2">
              <EnvelopeIcon className="h-4 w-4 shrink-0" />
              <span>Please verify your email to enable job alerts.</span>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                className="font-semibold underline hover:opacity-80 disabled:opacity-60"
              >
                {resending ? 'Sending…' : 'Resend email'}
              </button>
            </div>
            <button
              type="button"
              onClick={() => setBannerDismissed(true)}
              className="shrink-0 text-fg-subtle hover:text-fg"
              aria-label="Dismiss"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="px-4 py-6 md:p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              className="mx-auto w-full min-w-0 max-w-7xl"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <MobileNav />
    </div>
  )
}
