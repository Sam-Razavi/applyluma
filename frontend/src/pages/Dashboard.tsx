import { Link } from 'react-router-dom'
import { FadeIn } from '../components/ui/FadeIn'
import { useAuthStore } from '../stores'

const STATS = [
  { label: 'Total CVs', value: '—', sub: 'Upload your first CV', href: '/cvs' },
  { label: 'Job Listings', value: '—', sub: 'Add a job description', href: '/jobs' },
  { label: 'AI Analyses', value: '—', sub: 'Run your first analysis', href: '/ai-tailor' },
]

const QUICK_ACTIONS = [
  {
    title: 'Upload CV',
    description: 'Add a CV in PDF or DOCX format for AI analysis.',
    href: '/cvs',
    iconBg: 'bg-blue-100',
    icon: (
      <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    btnClass: 'bg-blue-600 hover:bg-blue-700',
  },
  {
    title: 'Add Job',
    description: 'Paste a job description to extract keywords and track.',
    href: '/jobs',
    iconBg: 'bg-violet-100',
    icon: (
      <svg className="h-6 w-6 text-violet-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
      </svg>
    ),
    btnClass: 'bg-violet-600 hover:bg-violet-700',
  },
  {
    title: 'AI Tailor',
    description: 'Match your CV to a job and get actionable improvement tips.',
    href: '/ai-tailor',
    iconBg: 'bg-brand-100',
    icon: (
      <svg className="h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
    btnClass: 'bg-brand-600 hover:bg-brand-700',
  },
]

export default function Dashboard() {
  const { user } = useAuthStore()
  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there'

  return (
    <FadeIn>
    <div className="space-y-8">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {firstName} 👋
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here's an overview of your job search.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {STATS.map(({ label, value, sub, href }) => (
          <Link
            key={label}
            to={href}
            className="group bg-white rounded-xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-sm transition"
          >
            <p className="text-sm font-medium text-gray-500">{label}</p>
            <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
            <p className="mt-1 text-xs text-gray-400 group-hover:text-brand-500 transition-colors">
              {sub} →
            </p>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-base font-semibold text-gray-900 mb-3">Quick actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {QUICK_ACTIONS.map(({ title, description, href, iconBg, icon, btnClass }) => (
            <div
              key={title}
              className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3"
            >
              <div className={`h-10 w-10 rounded-lg ${iconBg} flex items-center justify-center`}>
                {icon}
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
                <p className="mt-0.5 text-xs text-gray-500">{description}</p>
              </div>
              <Link
                to={href}
                className={`self-start inline-block text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${btnClass}`}
              >
                Get started
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="text-base font-semibold text-gray-900 mb-3">Recent activity</h2>
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <p className="text-sm text-gray-400">
            No activity yet — upload a CV or add a job to get started.
          </p>
        </div>
      </div>
    </div>
    </FadeIn>
  )
}
