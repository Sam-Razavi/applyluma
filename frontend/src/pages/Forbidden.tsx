import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { HomeIcon, ShieldExclamationIcon, Squares2X2Icon } from '@heroicons/react/24/outline'
import { FadeIn } from '../components/ui/FadeIn'
import { useAuthStore } from '../stores'

export default function Forbidden() {
  const token = useAuthStore((state) => state.token)
  const primaryDestination = token ? '/dashboard' : '/'
  const primaryLabel = token ? 'Go to dashboard' : 'Go home'

  return (
    <div className="min-h-screen bg-surface px-4 py-16 sm:px-6 lg:px-8">
      <FadeIn>
        <div className="mx-auto flex max-w-lg flex-col items-center text-center">
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-chip-warn text-chip-warn-fg"
          >
            <ShieldExclamationIcon className="h-8 w-8" aria-hidden="true" />
          </motion.div>

          <p className="text-sm font-semibold uppercase tracking-wide text-accent-text">
            403 · Access restricted
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-fg sm:text-4xl">
            This area isn't available to you
          </h1>
          <p className="mt-4 text-base leading-7 text-fg-subtle">
            You don't have permission to view this page. If you think this is a mistake,
            contact support.
          </p>

          <div className="mt-8 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            <Link
              to={primaryDestination}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            >
              {token ? (
                <Squares2X2Icon className="h-4 w-4" aria-hidden="true" />
              ) : (
                <HomeIcon className="h-4 w-4" aria-hidden="true" />
              )}
              {primaryLabel}
            </Link>
          </div>
        </div>
      </FadeIn>
    </div>
  )
}
