import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../stores'
import config from '../config/environment'

const API_URL = config.apiUrl

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  // Send cookies cross-origin so httpOnly auth cookies are included in every request.
  withCredentials: true,
})

function redirectToLogin(reason: 'session-expired') {
  const params = new URLSearchParams({ reason })
  const currentPath = `${window.location.pathname}${window.location.search}`

  if (window.location.pathname !== '/login') {
    params.set('next', currentPath)
  }

  window.location.assign(`/login?${params.toString()}`)
}

/** Read the csrf_token cookie (non-httpOnly) set by the server on login. */
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

// These paths must never trigger an auto-refresh attempt
const NO_REFRESH_PATHS = ['/auth/refresh', '/auth/login', '/auth/logout']

let isRefreshing = false
type QueueItem = { resolve: (token: string) => void; reject: (err: unknown) => void }
let failedQueue: QueueItem[] = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((item) => {
    if (error) item.reject(error)
    else item.resolve(token!)
  })
  failedQueue = []
}

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  const url = config.url ?? ''
  const isPublicAnalyticsEndpoint =
    (url.startsWith('/api/v1/analytics/') || url.startsWith('/api/analytics/')) &&
    !url.includes('/comparison')

  if (token && !isPublicAnalyticsEndpoint) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // Always add X-Requested-With so the server can distinguish AJAX from
  // form-POST CSRF attacks, and forward the CSRF token for state-changing
  // requests authenticated via cookie (no Authorization header).
  config.headers['X-Requested-With'] = 'XMLHttpRequest'
  if (!token && config.method && !['get', 'head', 'options'].includes(config.method.toLowerCase())) {
    const csrf = getCsrfToken()
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const url = originalRequest?.url ?? ''
    const { token, refreshToken, isAuthenticated } = useAuthStore.getState()

    // Attempt silent token refresh when:
    // - server returned 401
    // - user had an access token OR was previously authenticated (cookie flow)
    // - a refresh token is available OR we rely on the httpOnly refresh cookie
    // - this isn't already a retry
    // - this isn't the refresh/login/logout endpoint itself
    if (
      error.response?.status === 401 &&
      (token || isAuthenticated) &&
      !originalRequest._retry &&
      !NO_REFRESH_PATHS.some((p) => url.includes(p))
    ) {
      // Queue concurrent requests while one refresh is in flight
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Send refresh_token in body if available in memory (same session);
        // otherwise rely on the httpOnly refresh cookie (cookie-only clients).
        const refreshBody = refreshToken ? { refresh_token: refreshToken } : {}
        const res = await apiClient.post<{ access_token: string }>('/api/v1/auth/refresh', refreshBody)
        const newToken = res.data.access_token
        useAuthStore.getState().setToken(newToken)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        useAuthStore.getState().logout()
        redirectToLogin('session-expired')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // No refresh possible — if the user was authenticated, log them out
    if (error.response?.status === 401 && token) {
      useAuthStore.getState().logout()
      redirectToLogin('session-expired')
    }

    // Unverified user hitting a protected endpoint → send to /check-email
    if (error.response?.status === 403) {
      const detail = (error.response.data as Record<string, unknown>)?.detail
      const code = (detail as Record<string, unknown> | null)?.code
      if (code === 'EMAIL_NOT_VERIFIED' && window.location.pathname !== '/check-email') {
        window.location.assign('/check-email')
        return Promise.reject(error)
      }
    }

    // Normalise 429 responses to a consistent shape so every page can read
    // `error.response.data.detail` regardless of which endpoint fired it.
    if (error.response?.status === 429) {
      const raw = error.response.data as Record<string, unknown>
      const message =
        (raw?.detail as string) ||
        ((raw?.error as Record<string, unknown>)?.message as string) ||
        'Too many requests. Please try again later.'
      error.response.data = { detail: message, code: 'TOO_MANY_REQUESTS' }
    }

    return Promise.reject(error)
  },
)

export default apiClient
