import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRightIcon,
  BriefcaseIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import ErrorState from '../components/ui/ErrorState'
import { FadeIn } from '../components/ui/FadeIn'
import JobFreshnessStat from '../components/analytics/JobFreshnessStat'
import { getErrorMessage } from '../lib/errors'
import { useAuthStore } from '../stores'
import { useApplicationsStore } from '../stores/applications'
import { cvApi, jobApi } from '../services/api'
import DashboardActivityChart from '../components/applications/DashboardActivityChart'
import OnboardingChecklist from '../components/dashboard/OnboardingChecklist'
import type { CV, JobDescription } from '../types'

export default function Dashboard() {
  const { user } = useAuthStore()
  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there'
  const isNewUser = user?.created_at
    ? Date.now() - new Date(user.created_at).getTime() < 60 * 60 * 1000
    : false

  const applications = useApplicationsStore((s) => s.applications)
  const stats = useApplicationsStore((s) => s.stats)
  const applicationsError = useApplicationsStore((s) => s.error)
  const fetchApplications = useApplicationsStore((s) => s.fetchApplications)

  const [cvs, setCvs] = useState<CV[]>([])
  const [jds, setJds] = useState<JobDescription[]>([])
  const [loading, setLoading] = useState(true)
  const [cvJdError, setCvJdError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Dashboard | ApplyLuma'
    void Promise.all([
      fetchApplications(),
      cvApi
        .list()
        .then(setCvs)
        .catch((err: unknown) => setCvJdError(getErrorMessage(err, 'Failed to load your CVs and job descriptions'))),
      jobApi
        .list()
        .then(setJds)
        .catch((err: unknown) => setCvJdError(getErrorMessage(err, 'Failed to load your CVs and job descriptions'))),
    ]).finally(() => setLoading(false))
  }, [fetchApplications])

  const activeApplications = (stats.applied ?? 0) + (stats.phone_screen ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0)
  const recentApplications = [...applications]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayCount = applications.filter((a) => new Date(a.created_at) >= today).length
  const upcomingInterviews = [...applications]
    .filter((a) => a.interview_date && new Date(a.interview_date) >= today)
    .sort((a, b) => new Date(a.interview_date!).getTime() - new Date(b.interview_date!).getTime())
    .slice(0, 4)

  const STATUS_COLOR: Record<string, string> = {
    wishlist: 'bg-chip-neutral text-chip-neutral-fg',
    applied: 'bg-chip-accent text-chip-accent-fg',
    phone_screen: 'bg-chip-warn text-chip-warn-fg',
    interview: 'bg-chip-accent text-chip-accent-fg',
    offer: 'bg-chip-success text-chip-success-fg',
    rejected: 'bg-chip-danger text-chip-danger-fg',
    withdrawn: 'bg-chip-neutral text-fg-subtle',
  }

  const topStats = [
    {
      label: 'CVs',
      value: loading ? '—' : cvJdError ? '—' : String(cvs.length),
      sub: cvJdError
        ? 'Could not load'
        : cvs.length === 0
          ? 'Upload your first CV'
          : cvs.length === 1
            ? '1 CV uploaded'
            : `${cvs.length} CVs uploaded`,
      href: '/cvs',
      icon: <DocumentTextIcon className="h-5 w-5 text-accent-text" />,
      bg: 'bg-chip-accent',
    },
    {
      label: 'Applications',
      value: loading ? '—' : String(applications.length),
      sub: loading
        ? '—'
        : todayCount > 0
          ? `${todayCount} added today · ${activeApplications} active`
          : activeApplications > 0
            ? `${activeApplications} active`
            : 'None in progress',
      href: '/applications',
      icon: <BriefcaseIcon className="h-5 w-5 text-accent-text" />,
      bg: 'bg-accent-muted',
    },
    {
      label: 'Job Descriptions',
      value: loading ? '—' : cvJdError ? '—' : String(jds.length),
      sub: cvJdError ? 'Could not load' : jds.length === 0 ? 'Add a job to get started' : `${jds.length} saved`,
      href: '/jobs',
      icon: <MagnifyingGlassIcon className="h-5 w-5 text-accent-text" />,
      bg: 'bg-chip-accent',
    },
  ]

  const quickActions = [
    {
      title: 'Upload CV',
      description: 'Add a CV in PDF, DOCX, or Markdown format for AI analysis.',
      href: '/cvs',
      icon: <DocumentTextIcon className="h-6 w-6 text-accent-text" />,
      iconBg: 'bg-chip-accent',
      btnClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    },
    {
      title: 'Discover Jobs',
      description: 'Browse AI-matched Swedish job listings from multiple sources.',
      href: '/discover',
      icon: <MagnifyingGlassIcon className="h-6 w-6 text-accent-text" />,
      iconBg: 'bg-chip-accent',
      btnClass: 'bg-violet-600 hover:bg-violet-700 text-white',
    },
    {
      title: 'Tailor with AI',
      description: 'Match your CV to a job and get targeted improvements.',
      href: '/ai-tailor',
      icon: <SparklesIcon className="h-6 w-6 text-accent-text" />,
      iconBg: 'bg-accent-muted',
      btnClass: 'bg-brand-600 hover:bg-brand-700 text-white',
    },
    {
      title: 'Market Analytics',
      description: 'Explore hiring trends, in-demand skills, and salary insights.',
      href: '/analytics',
      icon: <ChartBarIcon className="h-6 w-6 text-accent-text" />,
      iconBg: 'bg-chip-accent',
      btnClass: 'bg-cyan-600 hover:bg-cyan-700 text-white',
    },
  ]

  return (
    <FadeIn>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-fg ">
            {isNewUser ? `Welcome, ${firstName}! 🎉` : `Welcome back, ${firstName} 👋`}
          </h1>
          <p className="mt-1 text-sm text-fg-subtle ">
            Here's your job search at a glance.
          </p>
        </div>

        {/* Live ingestion stat — shows the platform is actively finding jobs */}
        <JobFreshnessStat />

        {/* Onboarding checklist — hidden once all 3 steps are done, or if the CV/JD load failed */}
        {!cvJdError && (
          <OnboardingChecklist hasCv={cvs.length > 0} hasJd={jds.length > 0} loading={loading} />
        )}

        {/* Stats row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {topStats.map(({ label, value, sub, href, icon, bg }) => (
            <Link
              key={label}
              to={href}
              className="group flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 transition hover:border-accent hover:shadow-md "
            >
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${bg}`}>
                {icon}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-fg-subtle ">{label}</p>
                <p className="text-2xl font-bold text-fg ">
                  {loading ? (
                    <span className="inline-block h-7 w-8 animate-pulse rounded bg-track" />
                  ) : value}
                </p>
                <p className="mt-0.5 truncate text-xs text-fg-subtle group-hover:text-accent-text transition-colors">
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
          <div className="rounded-2xl border border-line bg-surface p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-fg ">Application pipeline</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-accent-text hover:opacity-80">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-8 animate-pulse rounded-lg bg-track" />
                ))}
              </div>
            ) : applicationsError ? (
              <ErrorState size="compact" description={applicationsError} onRetry={fetchApplications} />
            ) : applications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-fg-subtle" />
                <p className="mt-2 text-sm text-fg-subtle">No applications yet</p>
                <Link to="/applications" className="mt-3 text-xs font-semibold text-accent-text hover:opacity-80">
                  Add your first →
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {[
                  { key: 'wishlist', label: 'Wishlist', color: 'bg-fg-subtle' },
                  { key: 'applied', label: 'Applied', color: 'bg-blue-500' },
                  { key: 'interview', label: 'Interview', color: 'bg-purple-500' },
                  { key: 'offer', label: 'Offer', color: 'bg-green-500' },
                ].map(({ key, label, color }) => {
                  const count = stats[key as keyof typeof stats] ?? 0
                  const total = applications.length
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-16 shrink-0 text-xs text-fg-subtle">{label}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-track">
                        <div
                          className={`h-full rounded-full ${color} transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-6 text-right text-xs font-semibold text-fg-muted ">
                        {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Recent applications */}
          <div className="rounded-2xl border border-line bg-surface p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-fg ">Recent applications</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-accent-text hover:opacity-80">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-10 animate-pulse rounded-lg bg-track" />
                ))}
              </div>
            ) : applicationsError ? (
              <ErrorState size="compact" description={applicationsError} onRetry={fetchApplications} />
            ) : recentApplications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-fg-subtle" />
                <p className="mt-2 text-sm text-fg-subtle">Nothing tracked yet</p>
                <Link to="/discover" className="mt-3 text-xs font-semibold text-accent-text hover:opacity-80">
                  Discover jobs →
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-line ">
                {recentApplications.map((app) => (
                  <li key={app.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-fg ">{app.company_name}</p>
                      <p className="truncate text-xs text-fg-subtle">{app.job_title}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[app.status] ?? 'bg-track text-fg-muted'}`}>
                      {app.status.replace('_', ' ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Upcoming interviews */}
        {!loading && upcomingInterviews.length > 0 && (
          <div className="rounded-2xl border border-accent-muted bg-surface p-5 ">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CalendarDaysIcon className="h-4 w-4 text-purple-500" />
                <h2 className="text-sm font-semibold text-fg ">Upcoming interviews</h2>
              </div>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-accent-text hover:opacity-80">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            <ul className="divide-y divide-line ">
              {upcomingInterviews.map((app) => {
                const date = new Date(app.interview_date!)
                const daysUntil = Math.ceil((date.getTime() - today.getTime()) / 86_400_000)
                const label = daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `In ${daysUntil} days`
                const urgency = daysUntil === 0 ? 'text-chip-danger-fg bg-chip-danger' : daysUntil <= 2 ? 'text-chip-warn-fg bg-chip-warn' : 'text-chip-accent-fg bg-chip-accent'
                return (
                  <li key={app.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-fg ">{app.company_name}</p>
                      <p className="truncate text-xs text-fg-subtle">{app.job_title} · {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${urgency}`}>{label}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-fg ">Quick actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {quickActions.map(({ title, description, href, icon, iconBg, btnClass }) => (
              <div
                key={title}
                className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5"
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg}`}>
                  {icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-fg ">{title}</h3>
                  <p className="mt-0.5 text-xs text-fg-subtle ">{description}</p>
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
