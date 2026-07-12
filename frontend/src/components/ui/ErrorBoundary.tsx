import * as Sentry from '@sentry/react'
import { Component, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { ease, variants } from '../../lib/animations'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

// Errors thrown when a dynamically-imported chunk can't be fetched — typically
// because a new deploy replaced the chunk the client's stale index.html points to.
const CHUNK_ERROR_RE = /dynamically imported module|loading chunk|importing a module script failed|failed to fetch/i
const RELOAD_FLAG = 'chunk-reload-attempted'

function isChunkLoadError(error: Error | null): boolean {
  return !!error && CHUNK_ERROR_RE.test(error.message)
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    // A stale chunk after a redeploy is transient — reload once to pull the
    // fresh index.html + chunks. The sessionStorage guard prevents reload loops.
    if (isChunkLoadError(error) && !sessionStorage.getItem(RELOAD_FLAG)) {
      sessionStorage.setItem(RELOAD_FLAG, '1')
      window.location.reload()
      return
    }
    console.error('[ErrorBoundary]', error, info.componentStack)
    Sentry.captureException(error, { contexts: { react: { componentStack: info.componentStack } } })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <motion.div
          initial={variants.scaleIn.initial}
          animate={variants.scaleIn.animate}
          transition={ease.standard}
          className="min-h-[400px] flex flex-col items-center justify-center gap-4 text-center p-8"
        >
          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="h-16 w-16 rounded-2xl bg-chip-danger flex items-center justify-center"
          >
            <ExclamationTriangleIcon className="h-8 w-8 text-chip-danger-fg" aria-hidden="true" />
          </motion.div>
          <h2 className="text-xl font-semibold text-fg">Something went wrong</h2>
          <p className="text-sm text-fg-subtle max-w-sm">
            Something on this page hit a snag. Try again, or head back if it keeps happening.
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            Try again
          </button>
        </motion.div>
      )
    }
    return this.props.children
  }
}
