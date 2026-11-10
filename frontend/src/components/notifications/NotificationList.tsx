import { useNavigate } from 'react-router-dom'
import { useNotificationsStore } from '../../stores/notifications'

// Where a notification of each kind leads. Kinds not listed (e.g. a message
// from an admin) just mark themselves read.
const LINKS: Record<string, string> = {
  email_status_suggestion: '/applications',
  application_stale: '/applications',
  deadline_reminder: '/applications',
  application: '/applications',
  applications: '/applications',
  high_match_alert: '/discover',
  jobs: '/discover',
  tailor_complete: '/ai-tailor',
  tailor_job: '/ai-tailor',
  cover_letter_complete: '/ai-tailor',
  cover_letter_job: '/ai-tailor',
  weekly_summary: '/dashboard',
}

interface Props {
  align?: 'left' | 'right'
  onNavigate?: () => void
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function NotificationList({ align = 'right', onNavigate }: Props) {
  const { notifications, unreadCount, isLoading, markRead, markAllRead } = useNotificationsStore()
  const navigate = useNavigate()

  return (
    <div
      className={`absolute ${align === 'left' ? 'left-0' : 'right-0'} z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-lg border border-line bg-raised shadow-2xl`}
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold text-fg">Notifications</h2>
        <button
          type="button"
          onClick={() => void markAllRead()}
          disabled={unreadCount === 0}
          className="text-xs font-medium text-accent-text hover:text-accent-text disabled:cursor-not-allowed disabled:text-fg-subtle"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {isLoading && notifications.length === 0 ? (
          <div className="space-y-3 p-4">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-16 animate-pulse rounded-md bg-track" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-fg-subtle">No notifications</div>
        ) : (
          notifications.map((notification) => (
            <button
              key={notification.id}
              type="button"
              onClick={() => {
                if (!notification.is_read) void markRead(notification.id)
                const link = LINKS[notification.type]
                if (link) {
                  onNavigate?.()
                  navigate(link)
                }
              }}
              className={`block w-full border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-surface-strong ${
                notification.is_read ? 'bg-surface' : 'bg-primary-50/60'
              }`}
            >
              <div className="flex items-start gap-3">
                <span
                  className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${
                    notification.is_read ? 'bg-transparent' : 'bg-primary-600'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-fg">{notification.title}</p>
                    <time className="flex-shrink-0 text-xs text-fg-subtle">
                      {formatDate(notification.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 line-clamp-3 whitespace-pre-line text-sm text-fg-muted">{notification.body}</p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
