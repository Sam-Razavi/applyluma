import { Link, NavLink } from 'react-router-dom'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { NAV_LINKS } from './navLinks'

interface Props {
  open: boolean
  onClose: () => void
}

export default function MobileNav({ open, onClose }: Props) {
  return (
    <div
      className={`fixed inset-0 z-50 md:hidden ${open ? 'pointer-events-auto' : 'pointer-events-none'}`}
      aria-hidden={!open}
    >
      <div
        className={`absolute inset-0 bg-black/30 transition-opacity duration-200 ${
          open ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={onClose}
      />
      <nav
        className={`absolute inset-y-0 left-0 flex w-full flex-col bg-white shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Mobile navigation"
      >
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
          <Link
            to="/dashboard"
            onClick={onClose}
            className="text-xl font-bold tracking-tight text-primary-600"
          >
            ApplyLuma
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
            aria-label="Close navigation menu"
          >
            <XMarkIcon className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto px-4 py-5">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `block rounded-xl px-4 py-3 text-base font-semibold transition ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
