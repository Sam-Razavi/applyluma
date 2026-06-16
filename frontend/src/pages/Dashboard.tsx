import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRightIcon,
  BriefcaseIcon,
  CalendarDaysIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { FadeIn } from '../components/ui/FadeIn'
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
  const fetchApplications = useApplicationsStore((s) => s.fetchApplications)

  const [cvs, setCvs] = useState<CV[]>([])
  const [jds, setJds] = useState<JobDescription[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    document.title = 'Dashboard | ApplyLuma'
    void Promise.all([
      fetchApplications(),
      cvApi.list().then(setCvs).catch((err: unknown) => console.error('Failed to load CVs', err)),
      jobApi.list().then(setJds).catch((err: unknown) => console.error('Failed to load job descriptions', err)),
    ]).finally(() => setLoading(false))
  }, [fetchApplications])

  const activeApplications = (stats.applied ?? 0) + (stats.phone_screen ?? 0) + (stats.interview ?? 0) + (stats.offer ?? 0)
  const recentApplications = [...applications]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const upcomingInterviews = [...applications]
    .filter((a) => a.interview_date && new Date(a.interview_date) >= today)
    .sort((a, b) => new Date(a.interview_date!).getTime() - new Date(b.interview_date!).getTime())
    .slice(0, 4)

  const STATUS_COLOR: Record<string, string> = {
    wishlist: 'bg-white/[0.04] text-white/55',
    applied: 'bg-[rgba(8,145,178,0.15)] text-cyan-300',
    phone_screen: 'bg-[rgba(245,158,11,0.14)] text-amber-300',
    interview: 'bg-[rgba(8,145,178,0.15)] text-cyan-300',
    offer: 'bg-[rgba(52,195,143,0.14)] text-emerald-300',
    rejected: 'bg-[rgba(229,72,77,0.12)] text-red-300',
    withdrawn: 'bg-white/[0.04] text-white/30',
  }

  const topStats = [
    {
      label: 'CVs',
      value: loading ? '—' : String(cvs.length),
      sub: cvs.length === 0 ? 'Upload your first CV' : cvs.length === 1 ? '1 CV uploaded' : `${cvs.length} CVs uploaded`,
      href: '/cvs',
      icon: <DocumentTextIcon className="h-5 w-5 text-blue-500" />,
      bg: 'bg-[rgba(8,145,178,0.15)]',
    },
    {
      label: 'Applications',
      value: loading ? '—' : String(applications.length),
      sub: activeApplications > 0 ? `${activeApplications} active` : 'None in progress',
      href: '/applications',
      icon: <BriefcaseIcon className="h-5 w-5 text-primary-400" />,
      bg: 'bg-primary-900/20',
    },
    {
      label: 'Job Descriptions',
      value: loading ? '—' : String(jds.length),
      sub: jds.length === 0 ? 'Add a job to get started' : `${jds.length} saved`,
      href: '/jobs',
      icon: <MagnifyingGlassIcon className="h-5 w-5 text-violet-500" />,
      bg: 'bg-[rgba(8,145,178,0.15)]',
    },
  ]

  const quickActions = [
    {
      title: 'Upload CV',
      description: 'Add a CV in PDF or DOCX format for AI analysis.',
      href: '/cvs',
      icon: <DocumentTextIcon className="h-6 w-6 text-cyan-300" />,
      iconBg: 'bg-[rgba(8,145,178,0.15)]',
      btnClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    },
    {
      title: 'Discover Jobs',
      description: 'Browse AI-matched Swedish job listings from multiple sources.',
      href: '/discover',
      icon: <MagnifyingGlassIcon className="h-6 w-6 text-cyan-300" />,
      iconBg: 'bg-[rgba(8,145,178,0.15)]',
      btnClass: 'bg-violet-600 hover:bg-violet-700 text-white',
    },
    {
      title: 'Tailor with AI',
      description: 'Match your CV to a job and get targeted improvements.',
      href: '/ai-tailor',
      icon: <SparklesIcon className="h-6 w-6 text-primary-400" />,
      iconBg: 'bg-primary-900/30',
      btnClass: 'bg-brand-600 hover:bg-brand-700 text-white',
    },
  ]

  return (
    <FadeIn>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white/90 ">
            {isNewUser ? `Welcome, ${firstName}! 🎉` : `Welcome back, ${firstName} 👋`}
          </h1>
          <p className="mt-1 text-sm text-white/30 ">
            Here's your job search at a glance.
          </p>
        </div>

        {/* Onboarding checklist — hidden once all 3 steps are done */}
        <OnboardingChecklist hasCv={cvs.length > 0} hasJd={jds.length > 0} loading={loading} />

        {/* Stats row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {topStats.map(({ label, value, sub, href, icon, bg }) => (
            <Link
              key={label}
              to={href}
              className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 transition hover:border-brand-300 hover:shadow-md "
            >
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${bg}`}>
                {icon}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-white/30 ">{label}</p>
                <p className="text-2xl font-bold text-white/90 ">
                  {loading ? (
                    <span className="inline-block h-7 w-8 animate-pulse rounded bg-white/[0.06]" />
                  ) : value}
                </p>
                <p className="mt-0.5 truncate text-xs text-white/30 group-hover:text-brand-500 transition-colors">
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
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 ">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white/90 ">Application pipeline</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-primary-400 hover:text-primary-300">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-8 animate-pulse rounded-lg bg-white/[0.04]" />
                ))}
              </div>
            ) : applications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-white/30" />
                <p className="mt-2 text-sm text-white/30">No applications yet</p>
                <Link to="/applications" className="mt-3 text-xs font-semibold text-primary-400 hover:text-primary-300">
                  Add your first →
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {[
                  { key: 'wishlist', label: 'Wishlist', color: 'bg-white/30' },
                  { key: 'applied', label: 'Applied', color: 'bg-blue-500' },
                  { key: 'interview', label: 'Interview', color: 'bg-purple-500' },
                  { key: 'offer', label: 'Offer', color: 'bg-green-500' },
                ].map(({ key, label, color }) => {
                  const count = stats[key as keyof typeof stats] ?? 0
                  const total = applications.length
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-16 shrink-0 text-xs text-white/30">{label}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/[0.04]">
                        <div
                          className={`h-full rounded-full ${color} transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-6 text-right text-xs font-semibold text-white/55 ">
                        {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Recent applications */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 ">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white/90 ">Recent applications</h2>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-primary-400 hover:text-primary-300">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-10 animate-pulse rounded-lg bg-white/[0.04]" />
                ))}
              </div>
            ) : recentApplications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <BriefcaseIcon className="h-8 w-8 text-white/30" />
                <p className="mt-2 text-sm text-white/30">Nothing tracked yet</p>
                <Link to="/discover" className="mt-3 text-xs font-semibold text-primary-400 hover:text-primary-300">
                  Discover jobs →
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-white/10 ">
                {recentApplications.map((app) => (
                  <li key={app.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white/90 ">{app.company_name}</p>
                      <p className="truncate text-xs text-white/30">{app.job_title}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[app.status] ?? 'bg-white/[0.04] text-white/55'}`}>
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
          <div className="rounded-2xl border border-[rgba(8,145,178,0.28)] bg-white/[0.04] p-5 ">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CalendarDaysIcon className="h-4 w-4 text-purple-500" />
                <h2 className="text-sm font-semibold text-white/90 ">Upcoming interviews</h2>
              </div>
              <Link to="/applications" className="flex items-center gap-1 text-xs font-medium text-primary-400 hover:text-primary-300">
                View all <ArrowRightIcon className="h-3.5 w-3.5" />
              </Link>
            </div>
            <ul className="divide-y divide-white/10 ">
              {upcomingInterviews.map((app) => {
                const date = new Date(app.interview_date!)
                const daysUntil = Math.ceil((date.getTime() - today.getTime()) / 86_400_000)
                const label = daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `In ${daysUntil} days`
                const urgency = daysUntil === 0 ? 'text-red-300 bg-[rgba(229,72,77,0.12)]' : daysUntil <= 2 ? 'text-amber-300 bg-[rgba(245,158,11,0.14)]' : 'text-cyan-300 bg-[rgba(8,145,178,0.15)]'
                return (
                  <li key={app.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white/90 ">{app.company_name}</p>
                      <p className="truncate text-xs text-white/30">{app.job_title} · {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
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
          <h2 className="mb-3 text-sm font-semibold text-white/90 ">Quick actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {quickActions.map(({ title, description, href, icon, iconBg, btnClass }) => (
              <div
                key={title}
                className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-5 "
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg}`}>
                  {icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-white/90 ">{title}</h3>
                  <p className="mt-0.5 text-xs text-white/30 ">{description}</p>
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
