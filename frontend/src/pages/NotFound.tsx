import { Link } from 'react-router-dom'
import { ArrowLeftIcon, HomeIcon, Squares2X2Icon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../stores'

export default function NotFound() {
  const token = useAuthStore((state) => state.token)
  const primaryDestination = token ? '/dashboard' : '/'
  const primaryLabel = token ? 'Go to dashboard' : 'Go home'

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-lg flex-col items-center text-center">
        <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 ring-1 ring-primary-100">
          <span className="text-lg font-bold">404</span>
        </div>

        <p className="text-sm font-semibold uppercase tracking-wide text-primary-600">
          Page not found
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
          This page is not available
        </h1>
        <p className="mt-4 text-base leading-7 text-gray-500">
          The link may be broken, or the page may have moved. You can return to a safe place
          and keep working from there.
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
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
            Go back
          </button>
        </div>
      </div>
    </div>
  )
}
