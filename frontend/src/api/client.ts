import axios, { type AxiosError } from 'axios'
import { useAuthStore } from '../stores'
import config from '../config/environment'

const API_URL = config.apiUrl

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

function redirectToLogin(reason: 'session-expired') {
  const params = new URLSearchParams({ reason })
  const currentPath = `${window.location.pathname}${window.location.search}`

  if (window.location.pathname !== '/login') {
    params.set('next', currentPath)
  }

  window.location.assign(`/login?${params.toString()}`)
}

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  const url = config.url ?? ''
  const isPublicAnalyticsEndpoint =
    (url.startsWith('/api/v1/analytics/') || url.startsWith('/api/analytics/')) &&
    !url.includes('/comparison')

  console.log(`[HTTP] ${config.method?.toUpperCase()} ${config.url} - token in store: ${token ? 'present' : 'null'}`)
  if (token && !isPublicAnalyticsEndpoint) {
    config.headers.Authorization = `Bearer ${token}`
    console.log('[HTTP] Authorization header set: Bearer', token.slice(0, 20) + '...')
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Only auto-logout if the user was already authenticated.
    // Without this guard, a failed login attempt (401) would reload the page
    // before the catch block in the login form could display the error.
    if (error.response?.status === 401 && useAuthStore.getState().token) {
      useAuthStore.getState().logout()
      redirectToLogin('session-expired')
    }

    // Normalise 429 responses to a consistent shape so every page can read
    // `error.response.data.detail` regardless of which endpoint fired it.
    // The analytics middleware returns a nested `error.message`; tailor and
    // other endpoints return a top-level `detail` string.
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
