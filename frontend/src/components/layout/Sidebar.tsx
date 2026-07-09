import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import {
  ArrowRightStartOnRectangleIcon,
  BookmarkIcon,
  BriefcaseIcon,
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  ChevronRightIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  HomeIcon,
  ShieldCheckIcon,
  SparklesIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../../stores'
import { useNotificationsStore } from '../../stores/notifications'
import { authApi } from '../../services/authApi'
import { adminApi } from '../../services/adminApi'
import UserAvatar from '../ui/UserAvatar'

type NavItem = {
  to: string
  label: string
  icon: typeof HomeIcon
  pip?: boolean
}

type NavSection = {
  label: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    label: 'Main',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: HomeIcon },
      { to: '/discover', label: 'Discover', icon: Squares2X2Icon, pip: true },
      { to: '/applications', label: 'Applications', icon: BriefcaseIcon, pip: true },
      { to: '/jobs', label: 'Saved Jobs', icon: BookmarkIcon },
      { to: '/cvs', label: 'CVs', icon: DocumentTextIcon },
    ],
  },
  {
    label: 'Tools',
    items: [
      { to: '/ai-tailor', label: 'AI Tailor', icon: SparklesIcon },
      { to: '/analytics', label: 'Analytics', icon: ChartBarIcon },
    ],
  },
  {
    label: 'Account',
    items: [
      { to: '/settings', label: 'Settings', icon: Cog6ToothIcon },
      { to: '/feedback', label: 'Feedback', icon: ChatBubbleLeftRightIcon },
    ],
  },
]

const ADMIN_ITEMS: NavItem[] = [
  { to: '/admin', label: 'Overview', icon: ShieldCheckIcon },
  { to: '/admin/users', label: 'Users', icon: ShieldCheckIcon },
  { to: '/admin/ai-jobs', label: 'AI Jobs', icon: ShieldCheckIcon },
  { to: '/admin/ai-costs', label: 'AI Costs', icon: ShieldCheckIcon },
  { to: '/admin/pipeline', label: 'Pipeline', icon: ShieldCheckIcon },
  { to: '/admin/raw-jobs', label: 'Raw Jobs', icon: ShieldCheckIcon },
  { to: '/admin/notifications', label: 'Notifications', icon: ShieldCheckIcon },
  { to: '/admin/billing', label: 'Billing', icon: ShieldCheckIcon },
  { to: '/admin/contact', label: 'Contact', icon: ShieldCheckIcon },
  { to: '/admin/system', label: 'System', icon: ShieldCheckIcon },
  { to: '/admin/audit-logs', label: 'Audit Logs', icon: ShieldCheckIcon },
]

function navClass({ isActive }: { isActive: boolean }) {
  return [
    'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'text-[var(--accent-text)]'
      : 'text-fg-muted hover:text-fg hover:bg-surface-strong',
  ].join(' ')
}

export default function Sidebar() {
  const { user, logout, refreshToken } = useAuthStore()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)
  const [newContactCount, setNewContactCount] = useState(0)

  const isAdmin = user?.role === 'admin'
  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    adminApi
      .listContactSubmissions({ status: 'new', size: 1 })
      .then((r) => {
        if (!cancelled) setNewContactCount(r.total)
      })
      .catch(() => {
        // badge is best-effort only
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin])

  async function handleLogout() {
    setSigningOut(true)
    try {
      await authApi.logout(refreshToken ?? undefined)
    } catch {
      /* fail open */
    }
    logout()
    navigate('/login')
  }

  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 hidden w-[224px] flex-col md:flex"
      style={{
        background: 'var(--bg-raised)',
        borderRight: '1px solid var(--glass-border)',
      }}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 px-5">
        <Link to="/dashboard" className="flex items-center gap-2">
          <span className="font-display text-lg font-bold tracking-tight text-fg">
            ApplyLuma
          </span>
          <span
            className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none"
            style={{
              background: 'var(--accent-muted)',
              color: 'var(--accent-text)',
            }}
          >
            Beta
          </span>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
              {section.label}
            </p>
            <div className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon, pip }) => (
                <NavLink key={to} to={to} className={navClass}>
                  {({ isActive }) => (
                    <span
                      className="flex w-full items-center gap-3 rounded-lg"
                      style={
                        isActive
                          ? {
                              background: 'var(--accent-muted)',
                              border: '1px solid rgba(8,145,178,0.28)',
                              margin: '-1px',
                              padding: '0',
                            }
                          : undefined
                      }
                    >
                      <span className="flex items-center gap-3 px-0">
                        <Icon className="h-4 w-4 shrink-0" />
                        <span>{label}</span>
                      </span>
                      {pip && unreadCount > 0 && (
                        <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent-text)]" />
                      )}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}

        {user?.role === 'admin' && (
          <div>
            <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
              Admin
            </p>
            <div className="space-y-0.5">
              {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/admin'}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'text-[var(--accent-text)] bg-[var(--accent-muted)]'
                        : 'text-fg-muted hover:text-fg hover:bg-surface-strong',
                    ].join(' ')
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{label}</span>
                  {to === '/admin/contact' && newContactCount > 0 && (
                    <span className="ml-auto rounded-full bg-chip-danger px-1.5 py-0.5 text-[10px] font-bold text-chip-danger-fg">
                      {newContactCount}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* User footer */}
      <div className="border-t border-line p-3">
        <Link
          to="/settings"
          className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-surface-strong"
        >
          <UserAvatar fullName={user?.full_name} email={user?.email} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-fg">
              {user?.full_name ?? user?.email ?? 'Account'}
            </p>
            <p className="truncate text-xs capitalize text-fg-subtle">
              {user?.role ?? 'user'} plan
            </p>
          </div>
          <ChevronRightIcon className="h-4 w-4 shrink-0 text-fg-subtle" />
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          disabled={signingOut}
          className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong hover:text-fg disabled:opacity-60"
        >
          <ArrowRightStartOnRectangleIcon className="h-4 w-4" />
          {signingOut ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    </aside>
  )
}
