import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRightStartOnRectangleIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../../stores'
import { authApi } from '../../services/authApi'
import NotificationBell from '../notifications/NotificationBell'
import UserAvatar from '../ui/UserAvatar'
import { NAV_LINKS } from './navLinks'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  async function handleLogout() {
    try { await authApi.logout() } catch { /* fail open */ }
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-6">
        {/* Logo */}
        <Link to="/dashboard" className="flex-shrink-0 text-xl font-bold text-primary-600 tracking-tight">
          ApplyLuma
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1 flex-1">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <NotificationBell />

          {/* User dropdown */}
          <div className="relative flex-shrink-0" ref={dropdownRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-2 rounded-xl px-2 py-1.5 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            aria-expanded={open}
            aria-haspopup="menu"
          >
            <UserAvatar fullName={user?.full_name} email={user?.email} />
            <span className="hidden sm:block max-w-[120px] truncate text-sm font-medium text-gray-700">
              {user?.full_name ?? user?.email ?? 'Account'}
            </span>
            <svg
              className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
              viewBox="0 0 20 20" fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {open && (
            <div className="absolute right-0 z-50 mt-1 w-56 rounded-xl border border-gray-200 bg-white py-1 shadow-lg" role="menu">
              <div className="flex items-center gap-3 border-b border-gray-100 px-4 py-3">
                <UserAvatar fullName={user?.full_name} email={user?.email} />
                <div className="min-w-0">
                  {user?.full_name && (
                    <p className="truncate text-sm font-semibold text-gray-900">{user.full_name}</p>
                  )}
                  <p className="truncate text-xs text-gray-400">{user?.email}</p>
                </div>
              </div>
              <Link
                to="/settings"
                className="flex items-center gap-2.5 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50"
              >
                <Cog6ToothIcon className="h-4 w-4 text-gray-400" />
                Settings
              </Link>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-red-50"
              >
                <ArrowRightStartOnRectangleIcon className="h-4 w-4" />
                Sign out
              </button>
            </div>
          )}
          </div>
        </div>
      </div>
    </header>
  )
}
