import { Link } from 'react-router-dom'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-gray-200 bg-white">
      <div className="container mx-auto px-4 py-10">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start sm:justify-between">
          {/* Brand */}
          <div>
            <Link to="/" className="text-lg font-bold text-indigo-600 tracking-tight">
              ApplyLuma
            </Link>
            <p className="mt-1 text-sm text-gray-400">AI-powered job search platform.</p>
          </div>

          {/* Links */}
          <div className="flex flex-wrap justify-center gap-x-8 gap-y-2 text-sm sm:justify-end">
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-gray-500 text-xs uppercase tracking-wide">Product</span>
              <Link to="/plans" className="text-gray-500 hover:text-gray-900 transition-colors">Pricing</Link>
              <Link to="/register" className="text-gray-500 hover:text-gray-900 transition-colors">Sign up free</Link>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-gray-500 text-xs uppercase tracking-wide">Legal</span>
              <Link to="/terms" className="text-gray-500 hover:text-gray-900 transition-colors">Terms of Service</Link>
              <Link to="/privacy" className="text-gray-500 hover:text-gray-900 transition-colors">Privacy Policy</Link>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-gray-500 text-xs uppercase tracking-wide">Support</span>
              <a
                href="mailto:support@applyluma.com"
                className="text-gray-500 hover:text-gray-900 transition-colors"
              >
                Contact us
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-gray-100 pt-6 text-center text-xs text-gray-400">
          © {year} ApplyLuma. All rights reserved.
        </div>
      </div>
    </footer>
  )
}
