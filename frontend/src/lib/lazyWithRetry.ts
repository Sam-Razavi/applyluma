import { lazy } from 'react'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function lazyWithRetry(importFn: () => Promise<{ default: React.ComponentType<any> }>) {
  return lazy(() =>
    importFn().catch((error: unknown) => {
      const key = 'chunk_reload_' + btoa(importFn.toString()).slice(0, 32)
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, '1')
        window.location.reload()
      }
      throw error
    }),
  )
}
