import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Bars3Icon, EnvelopeIcon, XMarkIcon } from '@heroicons/react/24/outline'
import Navbar from './Navbar'
import MobileNav from './MobileNav'
import { useInactivityLogout } from '../../hooks/useInactivityLogout'
import { useNotificationsStore } from '../../stores/notifications'
import { useAuthStore } from '../../stores'
import { authApi } from '../../services/authApi'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/applications': 'Applications',
  '/discover': 'Discover',
  '/saved-jobs': 'Saved Jobs',
  '/settings': 'Settings',
  '/cv': 'My CVs',
  '/jobs': 'Job Search',
}

export default function AppLayout() {
  useInactivityLogout()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {showVerifyBanner && (
        <div className="flex items-center justify-between gap-3 bg-amber-50 border-b border-amber-200 px-4 py-2.5 text-sm text-amber-800">
          <div className="flex items-center gap-2">
            <EnvelopeIcon className="h-4 w-4 shrink-0" />
            <span>Please verify your email to enable job alerts.</span>
            <button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className="underline font-medium hover:text-amber-900 disabled:opacity-60"
            >
              {resending ? 'Sending…' : 'Resend email'}
            </button>
          </div>
          <button
            type="button"
            onClick={() => setBannerDismissed(true)}
            className="shrink-0 text-amber-600 hover:text-amber-800"
            aria-label="Dismiss"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="hidden md:block">
        <Navbar />
      </div>

      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white md:hidden dark:border-gray-700 dark:bg-gray-800">
        <div className="flex h-16 items-center justify-between px-4">
          <Link
            to="/dashboard"
            onClick={() => window.scrollTo(0, 0)}
            className="text-xl font-bold tracking-tight text-primary-600"
          >
            ApplyLuma
          </Link>
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:text-gray-300 dark:hover:bg-gray-700"
            aria-label="Open navigation menu"
          >
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
      </header>

      <MobileNav open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 md:py-8 lg:px-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            className="w-full min-w-0"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
