import { useEffect, useRef, useState } from 'react'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores'

const NAV_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/cvs', label: 'My CVs' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/ai-tailor', label: 'AI Tailor' },
  { to: '/analytics', label: 'Analytics' },
]

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
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
    setMobileMenuOpen(false)
  }, [location.pathname])

  function handleLogout() {
    logout()
    setMobileMenuOpen(false)
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : (user?.email?.[0] ?? '?').toUpperCase()

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
          {/* User dropdown */}
          <div className="relative flex-shrink-0" ref={dropdownRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors duration-200 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            aria-expanded={open}
            aria-haspopup="menu"
          >
            <span className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-xs font-bold select-none">
              {initials}
            </span>
            <span className="hidden sm:block text-sm font-medium text-gray-700 max-w-[140px] truncate">
              {user?.full_name ?? user?.email ?? 'Account'}
            </span>
            <svg
              className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z"
                clipRule="evenodd"
              />
            </svg>
          </button>

          {open && (
            <div className="absolute right-0 z-50 mt-1 w-52 rounded-xl border border-gray-200 bg-white py-1 shadow-lg" role="menu">
              <div className="px-4 py-2.5 border-b border-gray-100">
                <p className="text-xs text-gray-400">Signed in as</p>
                <p className="text-sm font-medium text-gray-900 truncate">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
          </div>

          <button
            type="button"
            onClick={() => setMobileMenuOpen((current) => !current)}
            className="inline-flex items-center justify-center rounded-lg p-2 text-gray-600 transition-colors duration-200 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 md:hidden"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <XMarkIcon className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <nav className="border-t border-gray-200 bg-white md:hidden" aria-label="Mobile navigation">
          <div className="space-y-1 px-4 py-3">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-base font-medium transition-colors duration-200 ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  )
}
