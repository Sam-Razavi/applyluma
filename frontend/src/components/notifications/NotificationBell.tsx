import { useEffect, useRef, useState } from 'react'
import { BellIcon } from '@heroicons/react/24/outline'
import NotificationList from './NotificationList'
import { useNotificationsStore } from '../../stores/notifications'

interface Props {
  /** Which edge the dropdown lines up with: 'left' in the sidebar, 'right' in the phone header. */
  align?: 'left' | 'right'
}

// Notifications are loaded and refreshed by AppLayout, once for the whole
// shell; the sidebar and the phone header each render a bell.
export default function NotificationBell({ align = 'right' }: Props) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const unreadCount = useNotificationsStore((s) => s.unreadCount)

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onEscape)
    }
  }, [])

  return (
    <div ref={containerRef} className="relative flex-shrink-0">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="relative inline-flex h-10 w-10 items-center justify-center rounded-lg text-fg-muted transition-colors duration-200 hover:bg-surface-strong hover:text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        aria-expanded={open}
      >
        <BellIcon className="h-5 w-5" aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 min-w-5 rounded-full bg-red-600 px-1.5 py-0.5 text-center text-[10px] font-bold leading-none text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      {open && <NotificationList align={align} onNavigate={() => setOpen(false)} />}
    </div>
  )
}
