import { Link } from 'react-router-dom'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-line bg-surface">
      <div className="container mx-auto px-4 py-10">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start sm:justify-between">
          {/* Brand */}
          <div>
            <Link to="/" className="text-lg font-bold text-accent-text tracking-tight">
              ApplyLuma
            </Link>
            <p className="mt-1 text-sm text-fg-subtle">AI-powered job search platform.</p>
          </div>

          {/* Links */}
          <div className="flex flex-wrap justify-center gap-x-8 gap-y-2 text-sm sm:justify-end">
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-fg-subtle text-xs uppercase tracking-wide">Product</span>
              <Link to="/plans" className="text-fg-subtle hover:text-fg transition-colors">Pricing</Link>
              <Link to="/register" className="text-fg-subtle hover:text-fg transition-colors">Sign up free</Link>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-fg-subtle text-xs uppercase tracking-wide">Legal</span>
              <Link to="/terms" className="text-fg-subtle hover:text-fg transition-colors">Terms of Service</Link>
              <Link to="/privacy" className="text-fg-subtle hover:text-fg transition-colors">Privacy Policy</Link>
            </div>
            <div className="flex flex-col gap-1.5">
              <span className="font-semibold text-fg-subtle text-xs uppercase tracking-wide">Support</span>
              <Link
                to="/contact"
                className="text-fg-subtle hover:text-fg transition-colors"
              >
                Contact us
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-line pt-6 text-center text-xs text-fg-subtle">
          © {year} ApplyLuma. All rights reserved.
        </div>
      </div>
    </footer>
  )
}
