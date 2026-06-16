import { useNotificationsStore } from '../../stores/notifications'

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function NotificationList() {
  const { notifications, unreadCount, isLoading, markRead, markAllRead } = useNotificationsStore()

  return (
    <div className="absolute right-0 z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-lg border border-white/10 bg-[#0C1218] shadow-2xl">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h2 className="text-sm font-semibold text-white/90">Notifications</h2>
        <button
          type="button"
          onClick={() => void markAllRead()}
          disabled={unreadCount === 0}
          className="text-xs font-medium text-primary-400 hover:text-primary-300 disabled:cursor-not-allowed disabled:text-white/20"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {isLoading && notifications.length === 0 ? (
          <div className="space-y-3 p-4">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-16 animate-pulse rounded-md bg-white/[0.04]" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-white/30">No notifications</div>
        ) : (
          notifications.map((notification) => (
            <button
              key={notification.id}
              type="button"
              onClick={() => {
                if (!notification.is_read) void markRead(notification.id)
              }}
              className={`block w-full border-b border-white/10 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-white/[0.04] ${
                notification.is_read ? 'bg-white/[0.04]' : 'bg-primary-50/60'
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
                    <p className="text-sm font-semibold text-white/90">{notification.title}</p>
                    <time className="flex-shrink-0 text-xs text-white/30">
                      {formatDate(notification.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-white/55">{notification.body}</p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
