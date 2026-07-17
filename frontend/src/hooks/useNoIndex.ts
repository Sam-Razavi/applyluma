import { useEffect } from 'react'

/**
 * Injects <meta name="robots" content="noindex"> while the component is
 * mounted, and removes it on unmount. For routes served with HTTP 200 by
 * the SPA fallback (e.g. the catch-all 404 page) so they aren't indexed as
 * soft duplicates of the homepage.
 */
export function useNoIndex(): void {
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex'
    document.head.appendChild(meta)

    return () => {
      document.head.removeChild(meta)
    }
  }, [])
}
