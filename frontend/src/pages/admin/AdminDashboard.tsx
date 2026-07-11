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
    <div className="rounded-2xl border border-line bg-surface p-5 ">
      <p className="text-xs font-medium text-fg-subtle ">{label}</p>
      {loading ? (
        <div className="mt-1 h-8 w-16 animate-pulse rounded bg-track " />
      ) : (
        <p className="mt-1 text-3xl font-bold text-fg ">{value.toLocaleString()}</p>
      )}
      {sub && <p className="mt-0.5 text-xs text-fg-subtle">{sub}</p>}
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
          <h1 className="text-2xl font-bold text-fg ">Admin Overview</h1>
          <p className="mt-1 text-sm text-fg-subtle ">Platform-wide statistics at a glance.</p>
        </div>

        {error && (
          <div className="rounded-xl border border-chip-danger bg-chip-danger p-4 text-sm text-chip-danger-fg">{error}</div>
        )}

        {/* Users */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-fg-muted uppercase tracking-wide">
            Users
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <StatCard label="Total users" value={stats?.total_users ?? 0} loading={loading} />
            <StatCard
              label="Premium"
              value={stats?.premium_users ?? 0}
              loading={loading}
              sub={stats ? `${((stats.premium_users / Math.max(stats.total_users, 1)) * 100).toFixed(1)}% conversion` : undefined}
            />
            <StatCard label="Admins" value={stats?.admin_users ?? 0} loading={loading} />
            <StatCard label="New this week" value={stats?.new_users_this_week ?? 0} loading={loading} />
            <StatCard
              label="Verified"
              value={stats?.verified_users ?? 0}
              loading={loading}
              sub={stats ? `${((stats.verified_users / Math.max(stats.total_users, 1)) * 100).toFixed(1)}% verified` : undefined}
            />
          </div>
        </section>

        {/* AI Usage */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-fg-muted uppercase tracking-wide">
            AI Usage
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard label="Tailor jobs (total)" value={stats?.total_tailor_jobs ?? 0} loading={loading} />
            <StatCard label="Tailor pending" value={stats?.tailor_jobs_pending ?? 0} loading={loading} />
            <StatCard label="Tailor processing" value={stats?.tailor_jobs_processing ?? 0} loading={loading} />
            <StatCard label="Tailor complete" value={stats?.tailor_jobs_complete ?? 0} loading={loading} />
            <StatCard label="Tailor failed" value={stats?.tailor_jobs_failed ?? 0} loading={loading} />
            <StatCard label="Cover letters" value={stats?.total_cover_letters ?? 0} loading={loading} />
          </div>
        </section>

        {/* Content */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-fg-muted uppercase tracking-wide">
            Content
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="CVs uploaded" value={stats?.total_cvs ?? 0} loading={loading} />
            <StatCard label="Job descriptions" value={stats?.total_job_descriptions ?? 0} loading={loading} />
            <StatCard label="Applications tracked" value={stats?.total_applications ?? 0} loading={loading} />
          </div>
        </section>

        {/* Quick links */}
        <div className="flex flex-wrap gap-3">
          {[
            ['/admin/users', 'Manage Users'],
            ['/admin/ai-jobs', 'AI Jobs'],
            ['/admin/ai-costs', 'AI Costs'],
            ['/admin/pipeline', 'Pipeline Health'],
            ['/admin/raw-jobs', 'Raw Jobs'],
            ['/admin/notifications', 'Notifications'],
            ['/admin/billing', 'Billing'],
            ['/admin/contact', 'Contact Inbox'],
            ['/admin/system', 'System Health'],
            ['/admin/audit-logs', 'Audit Logs'],
          ].map(([to, label]) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              {label} <ArrowRightIcon className="h-4 w-4" />
            </Link>
          ))}
        </div>
      </div>
    </FadeIn>
  )
}
