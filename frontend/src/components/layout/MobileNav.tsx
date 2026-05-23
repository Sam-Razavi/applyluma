import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { ArrowRightStartOnRectangleIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { NAV_LINKS } from './navLinks'
import { spring } from '../../lib/animations'
import { useAuthStore } from '../../stores'
import { authApi } from '../../services/authApi'
import UserAvatar from '../ui/UserAvatar'

interface Props {
  open: boolean
  onClose: () => void
}

export default function MobileNav({ open, onClose }: Props) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return

    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [onClose, open])

  async function handleLogout() {
    onClose()
    try { await authApi.logout() } catch { /* fail open */ }
    logout()
    navigate('/login')
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <motion.div
            key="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/30"
            onClick={onClose}
          />
          <motion.nav
            key="drawer"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={spring.snappy}
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-2xl dark:bg-gray-800"
            aria-label="Mobile navigation"
          >
            <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4 dark:border-gray-700">
              <Link
                to="/settings"
                onClick={onClose}
                className="flex items-center gap-2.5 min-w-0"
              >
                <UserAvatar fullName={user?.full_name} email={user?.email} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">
                    {user?.full_name ?? user?.email ?? 'Account'}
                  </p>
                  {user?.full_name && (
                    <p className="truncate text-xs text-gray-400">{user.email}</p>
                  )}
                </div>
              </Link>
              <button
                type="button"
                onClick={onClose}
                className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:text-gray-300 dark:hover:bg-gray-700"
                aria-label="Close navigation menu"
              >
                <XMarkIcon className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>

            <div className="flex-1 space-y-2 overflow-y-auto px-4 py-5">
              {NAV_LINKS.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `block rounded-xl px-4 py-3 text-base font-semibold transition ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-200 dark:hover:bg-gray-700'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>

            <div className="border-t border-gray-200 px-4 py-4 dark:border-gray-700">
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-base font-semibold text-red-600 transition hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <ArrowRightStartOnRectangleIcon className="h-5 w-5" />
                Sign out
              </button>
            </div>
          </motion.nav>
        </div>
      )}
    </AnimatePresence>
  )
}
