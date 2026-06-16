import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRightIcon } from '@heroicons/react/24/outline'
import { FadeIn } from '../../components/ui/FadeIn'
import { adminApi, type AdminOverviewStats } from '../../services/adminApi'

function StatCard({
  label,
  value,
  loading,
  sub,
}: {
  label: string
  value: number
  loading: boolean
  sub?: string
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
      {loading ? (
        <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      ) : (
        <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{value.toLocaleString()}</p>
      )}
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminOverviewStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Admin — ApplyLuma'
    adminApi
      .getStats()
      .then(setStats)
      .catch(() => setError('Failed to load stats'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <FadeIn>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Overview</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Platform-wide statistics at a glance.</p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        {/* Users */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Users
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total users" value={stats?.total_users ?? 0} loading={loading} />
            <StatCard
              label="Premium"
              value={stats?.premium_users ?? 0}
              loading={loading}
              sub={stats ? `${((stats.premium_users / Math.max(stats.total_users, 1)) * 100).toFixed(1)}% conversion` : undefined}
            />
            <StatCard label="Admins" value={stats?.admin_users ?? 0} loading={loading} />
            <StatCard label="New this week" value={stats?.new_users_this_week ?? 0} loading={loading} />
          </div>
        </section>

        {/* AI Usage */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            AI Usage
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Tailor jobs (total)" value={stats?.total_tailor_jobs ?? 0} loading={loading} />
            <StatCard label="Tailor complete" value={stats?.tailor_jobs_complete ?? 0} loading={loading} />
            <StatCard label="Tailor failed" value={stats?.tailor_jobs_failed ?? 0} loading={loading} />
            <StatCard label="Cover letters" value={stats?.total_cover_letters ?? 0} loading={loading} />
          </div>
        </section>

        {/* Content */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Content
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="CVs uploaded" value={stats?.total_cvs ?? 0} loading={loading} />
            <StatCard label="Job descriptions" value={stats?.total_job_descriptions ?? 0} loading={loading} />
            <StatCard label="Applications tracked" value={stats?.total_applications ?? 0} loading={loading} />
          </div>
        </section>

        {/* Quick links */}
        <div className="flex gap-3">
          <Link
            to="/admin/users"
            className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
          >
            Manage Users <ArrowRightIcon className="h-4 w-4" />
          </Link>
          <Link
            to="/admin/pipeline"
            className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
          >
            Pipeline Health <ArrowRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </FadeIn>
  )
}
