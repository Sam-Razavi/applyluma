import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Bars3Icon } from '@heroicons/react/24/outline'
import Navbar from './Navbar'
import MobileNav from './MobileNav'
import { useInactivityLogout } from '../../hooks/useInactivityLogout'
import { useNotificationsStore } from '../../stores/notifications'

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
  const location = useLocation()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)

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
