import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRightStartOnRectangleIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../../stores'
import { authApi } from '../../services/authApi'
import NotificationBell from '../notifications/NotificationBell'
import UserAvatar from '../ui/UserAvatar'
import { ADMIN_NAV_LINKS, NAV_LINKS } from './navLinks'

export default function Navbar() {
  const { user, logout, refreshToken } = useAuthStore()
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
    try { await authApi.logout(refreshToken ?? undefined) } catch { /* fail open */ }
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-6">
        {/* Logo */}
        <Link to="/dashboard" className="flex-shrink-0 flex items-center gap-2">
          <span className="text-xl font-bold text-accent-text tracking-tight">ApplyLuma</span>
          <span className="rounded-full bg-chip-warn px-2 py-0.5 text-xs font-semibold text-chip-warn-fg leading-none">
            Beta
          </span>
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
                    ? 'bg-primary-900/20 text-accent-text'
                    : 'text-fg-muted hover:text-fg hover:bg-surface-strong'
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
            className="flex items-center gap-2 rounded-xl px-2 py-1.5 transition-colors hover:bg-surface-strong focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            aria-expanded={open}
            aria-haspopup="menu"
          >
            <UserAvatar fullName={user?.full_name} email={user?.email} />
            <span className="hidden sm:block max-w-[120px] truncate text-sm font-medium text-fg-muted">
              {user?.full_name ?? user?.email ?? 'Account'}
            </span>
            <svg
              className={`h-4 w-4 text-fg-subtle transition-transform ${open ? 'rotate-180' : ''}`}
              viewBox="0 0 20 20" fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {open && (
            <div className="absolute right-0 z-50 mt-1 w-56 rounded-xl border border-line bg-surface py-1 shadow-lg" role="menu">
              <div className="flex items-center gap-3 border-b border-line px-4 py-3">
                <UserAvatar fullName={user?.full_name} email={user?.email} />
                <div className="min-w-0">
                  {user?.full_name && (
                    <p className="truncate text-sm font-semibold text-fg">{user.full_name}</p>
                  )}
                  <p className="truncate text-xs text-fg-subtle">{user?.email}</p>
                </div>
              </div>
              <Link
                to="/settings"
                className="flex items-center gap-2.5 px-4 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-strong"
              >
                <Cog6ToothIcon className="h-4 w-4 text-fg-subtle" />
                Settings
              </Link>
              {user?.role === 'admin' && (
                <>
                  <div className="my-1 border-t border-line" />
                  {ADMIN_NAV_LINKS.map(({ to, label }) => (
                    <Link
                      key={to}
                      to={to}
                      className="flex items-center gap-2.5 px-4 py-2 text-sm text-chip-danger-fg transition-colors hover:bg-chip-danger"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                      </svg>
                      Admin — {label}
                    </Link>
                  ))}
                </>
              )}
              <div className="my-1 border-t border-line" />
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-chip-danger-fg transition-colors hover:bg-chip-danger"
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
