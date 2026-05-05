import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="max-w-md mx-auto text-center py-20">
      <p className="text-6xl font-bold text-indigo-600 mb-4">404</p>
      <h1 className="text-2xl font-semibold text-gray-900 mb-3">Page not found</h1>
      <p className="text-gray-500 mb-8">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="text-indigo-600 font-medium hover:underline">
        Go back home
      </Link>
    </div>
  )
}
