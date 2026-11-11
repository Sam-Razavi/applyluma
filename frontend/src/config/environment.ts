// Environment configuration
// A trailing slash in VITE_API_URL would turn hand-built links such as the
// OAuth buttons' `${apiUrl}/api/v1/...` into `//api/v1/...`, which 404s.
export const config = {
  apiUrl: (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, ''),
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
} as const

export default config

