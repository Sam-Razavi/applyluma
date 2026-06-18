import { NavLink } from 'react-router-dom'
import {
  BriefcaseIcon,
  HomeIcon,
  ShieldCheckIcon,
  Squares2X2Icon,
  SparklesIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline'
import { useNotificationsStore } from '../../stores/notifications'
import { useAuthStore } from '../../stores'

type Tab = {
  to: string
  label: string
  icon: typeof HomeIcon
  pip?: boolean
}

const BASE_TABS: Tab[] = [
  { to: '/dashboard', label: 'Home', icon: HomeIcon },
  { to: '/discover', label: 'Discover', icon: Squares2X2Icon, pip: true },
  { to: '/jobs', label: 'Saved', icon: BriefcaseIcon },
  { to: '/ai-tailor', label: 'AI Tailor', icon: SparklesIcon },
]

const ADMIN_TAB: Tab = { to: '/admin', label: 'Admin', icon: ShieldCheckIcon }
const PROFILE_TAB: Tab = { to: '/settings', label: 'Profile', icon: UserCircleIcon }

export default function MobileNav() {
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const user = useAuthStore((s) => s.user)

  const tabs = user?.role === 'admin'
    ? [...BASE_TABS, ADMIN_TAB, PROFILE_TAB]
    : [...BASE_TABS, PROFILE_TAB]

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-[100] flex md:hidden"
      style={{
        background: 'rgba(8,14,18,0.92)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderTop: '1px solid var(--glass-border)',
        paddingBottom: 'env(safe-area-inset-bottom, 8px)',
      }}
      aria-label="Mobile navigation"
    >
      {tabs.map(({ to, label, icon: Icon, pip }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            [
              'relative flex min-h-[44px] flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] font-medium transition-colors',
              isActive ? 'text-[var(--accent-text)]' : 'text-white/45',
            ].join(' ')
          }
        >
          <span className="relative">
            <Icon className="h-5 w-5" />
            {pip && unreadCount > 0 && (
              <span className="absolute -right-1 -top-0.5 h-2 w-2 rounded-full bg-[var(--accent-text)]" />
            )}
          </span>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
