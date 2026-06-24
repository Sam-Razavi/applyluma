// Suspense fallback shown while a lazily-loaded route chunk is fetched.
// `fullPage` covers the whole viewport (top-level boundary); the default
// content variant fills the app shell's content area so the nav stays visible.
export default function RouteFallback({ fullPage = false }: { fullPage?: boolean }) {
  return (
    <div
      className={`flex items-center justify-center ${fullPage ? 'min-h-screen bg-surface' : 'min-h-[60vh]'}`}
      role="status"
      aria-label="Loading"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
    </div>
  )
}
