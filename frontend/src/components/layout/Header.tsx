import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white/[0.04] border-b border-white/10">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-cyan-300 tracking-tight">
          ApplyLuma
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-sm text-white/55 hover:text-white/90 transition-colors"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Get started
          </Link>
        </nav>
      </div>
    </header>
  )
}
