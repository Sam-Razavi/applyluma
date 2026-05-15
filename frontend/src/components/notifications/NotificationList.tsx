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
    <div className="absolute right-0 z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-900">Notifications</h2>
        <button
          type="button"
          onClick={() => void markAllRead()}
          disabled={unreadCount === 0}
          className="text-xs font-medium text-primary-600 hover:text-primary-700 disabled:cursor-not-allowed disabled:text-gray-300"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {isLoading && notifications.length === 0 ? (
          <div className="space-y-3 p-4">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-16 animate-pulse rounded-md bg-gray-100" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">No notifications</div>
        ) : (
          notifications.map((notification) => (
            <button
              key={notification.id}
              type="button"
              onClick={() => {
                if (!notification.is_read) void markRead(notification.id)
              }}
              className={`block w-full border-b border-gray-100 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-gray-50 ${
                notification.is_read ? 'bg-white' : 'bg-primary-50/60'
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
                    <p className="text-sm font-semibold text-gray-900">{notification.title}</p>
                    <time className="flex-shrink-0 text-xs text-gray-400">
                      {formatDate(notification.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-gray-600">{notification.body}</p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
