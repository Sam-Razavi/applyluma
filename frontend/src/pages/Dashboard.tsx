import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRightIcon,
  BriefcaseIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { FadeIn } from '../components/ui/FadeIn'
import { useAuthStore } from '../stores'
import { useApplicationsStore } from '../stores/applications'
import { cvApi, jobApi } from '../services/api'
import DashboardActivityChart from '../components/applications/DashboardActivityChart'
import type { CV, JobDescription } from '../types'

export default function Dashboard() {
  const { user } = useAuthStore()
  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there'

  const applications = useApplicationsStore((s) => s.applications)
  const stats = useApplicationsStore((s) => s.stats)
  const fetchApplications = useApplicationsStore((s) => s.fetchApplications)

  const [cvs, setCvs] = useState<CV[]>([])
  const [jds, setJds] = useState<JobDescription[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    document.title = 'Dashboard | ApplyLuma'
    void Promise.all([
      fetchApplications(),
      cvApi.list().then(setCvs).catch(() => {}),
      jobApi.list().then(setJds).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [fetchApplications])

  const activeApplications = (stats.applied ?? 0) + (stats.phone_screen ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0)
  const recentApplications = [...applications]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const STATUS_COLOR: Record<string, string> = {
    wishlist: 'bg-gray-100 text-gray-600',
    applied: 'bg-blue-50 text-blue-700',
    phone_screen: 'bg-yellow-50 text-yellow-700',
    interview: 'bg-purple-50 text-purple-700',
    offer: 'bg-green-50 text-green-700',
    rejected: 'bg-red-50 text-red-600',
    withdrawn: 'bg-gray-100 text-gray-500',
  }

  const topStats = [
    {
      label: 'CVs',
      value: loading ? '—' : String(cvs.length),
      sub: cvs.length === 0 ? 'Upload your first CV' : cvs.length === 1 ? '1 CV uploaded' : `${cvs.length} CVs uploaded`,
      href: '/cvs',
      icon: <DocumentTextIcon className="h-5 w-5 text-blue-500" />,
      bg: 'bg-blue-50',
    },
    {
      label: 'Applications',
      value: loading ? '—' : String(applications.length),
      sub: activeApplications > 0 ? `${activeApplications} active` : 'None in progress',
      href: '/applications',
      icon: <BriefcaseIcon className="h-5 w-5 text-brand-500" />,
      bg: 'bg-brand-50',
    },
    {
      label: 'Job Descriptions',
      value: loading ? '—' : String(jds.length),
      sub: jds.length === 0 ? 'Add a job to get started' : `${jds.length} saved`,
      href: '/jobs',
      icon: <MagnifyingGlassIcon className="h-5 w-5 text-violet-500" />,
      bg: 'bg-violet-50',
    },
  ]

  const quickActions = [
    {
      title: 'Upload CV',
      description: 'Add a CV in PDF or DOCX format for AI analysis.',
      href: '/cvs',
      icon: <DocumentTextIcon className="h-6 w-6 text-blue-600" />,
      iconBg: 'bg-blue-100',
      btnClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    },
    {
      title: 'Discover Jobs',
      description: 'Browse AI-matched Swedish job listings from multiple sources.',
      href: '/discover',
      icon: <MagnifyingGlassIcon className="h-6 w-6 text-violet-600" />,
      iconBg: 'bg-violet-100',
      btnClass: 'bg-violet-600 hover:bg-violet-700 text-white',
    },
    {
      title: 'Tailor with AI',
      description: 'Match your CV to a job and get targeted improvements.',
      href: '/ai-tailor',
      icon: <SparklesIcon className="h-6 w-6 text-brand-600" />,
      iconBg: 'bg-brand-100',
      btnClass: 'bg-brand-600 hover:bg-brand-700 text-white',
    },
  ]

  return (
    <FadeIn>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {firstName} 👋
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Here's your job search at a glance.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {topStats.map(({ label, value, sub, href, icon, bg }) => (
            <Link
              key={label}
              to={href}
              className="group flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-5 transition hover:border-brand-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
            >
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${bg}`}>
                {icon}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {loading ? (
                    <span className="inline-block h-7 w-8 animate-pulse rounded bg-gray-200" />
                  ) : value}
                </p>
                <p className="mt-0.5 truncate text-xs text-gray-400 group-hover:text-brand-500 transition-colors">
                  {sub}
                </p>
              </div>
            </Link>
          ))}
        </div>

        {/* Activity chart */}
        <DashboardActivityChart />

        {/* Pipeline snapshot + Recent activity */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Pipeline snapshot */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Application pipeline</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-8 animate-pulse rounded-lg bg-gray-100" />
                ))}
              </div>
            ) : applications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-400">No applications yet</p>
                <Link to="/applications" className="mt-3 text-xs font-semibold text-brand-600 hover:text-brand-700">
                  Add your first →
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {[
                  { key: 'wishlist', label: 'Wishlist', color: 'bg-gray-400' },
                  { key: 'applied', label: 'Applied', color: 'bg-blue-500' },
                  { key: 'interview', label: 'Interview', color: 'bg-purple-500' },
                  { key: 'offer', label: 'Offer', color: 'bg-green-500' },
                ].map(({ key, label, color }) => {
                  const count = stats[key as keyof typeof stats] ?? 0
                  const total = applications.length
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-16 shrink-0 text-xs text-gray-500">{label}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className={`h-full rounded-full ${color} transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-6 text-right text-xs font-semibold text-gray-700 dark:text-gray-300">
                        {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Recent applications */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Recent applications</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-10 animate-pulse rounded-lg bg-gray-100" />
                ))}
              </div>
            ) : recentApplications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-400">Nothing tracked yet</p>
                <Link to="/discover" className="mt-3 text-xs font-semibold text-brand-600 hover:text-brand-700">
                  Discover jobs →
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                {recentApplications.map((app) => (
                  <li key={app.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900 dark:text-white">{app.company_name}</p>
                      <p className="truncate text-xs text-gray-400">{app.job_title}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[app.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {app.status.replace('_', ' ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Quick actions */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Quick actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {quickActions.map(({ title, description, href, icon, iconBg, btnClass }) => (
              <div
                key={title}
                className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg}`}>
                  {icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{description}</p>
                </div>
                <Link
                  to={href}
                  className={`self-start rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${btnClass}`}
                >
                  Get started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </FadeIn>
  )
}
