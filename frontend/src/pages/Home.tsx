import { Link } from 'react-router-dom'

const FEATURES = [
  {
    icon: '🎯',
    title: 'AI CV Tailor',
    description:
      'Paste a job description and ApplyLuma rewrites your CV section by section to match — you review every change before saving.',
  },
  {
    icon: '🔍',
    title: 'Swedish Job Discovery',
    description:
      'Browse thousands of jobs from Platsbanken, Jobbsafari, and Indeed.se with an AI match score calculated against your own CV.',
  },
  {
    icon: '✉️',
    title: 'Cover Letter Generator',
    description:
      'Generate a polished cover letter in your preferred tone — formal, friendly, or concise — and edit it before sending.',
  },
  {
    icon: '📋',
    title: 'Application Tracking',
    description:
      'Log every application, track statuses, and see analytics on your job search progress all in one place.',
  },
]

const STEPS = [
  { number: '01', title: 'Upload your CV', description: 'PDF or Word — we parse it automatically.' },
  { number: '02', title: 'Add a job you want', description: 'Paste the URL and we extract everything for you.' },
  { number: '03', title: 'Let AI do the work', description: 'Tailor your CV and generate a cover letter in seconds.' },
]

export default function Home() {
  return (
    <div className="space-y-24 pb-16">

      {/* Hero */}
      <div className="max-w-3xl mx-auto text-center pt-16">
        <span className="inline-block rounded-full bg-[rgba(8,145,178,0.15)] px-4 py-1.5 text-sm font-medium text-cyan-300 mb-6">
          Now in Beta — free to try
        </span>
        <h1 className="text-5xl font-bold text-white/90 mb-6 leading-tight">
          Land your next job{' '}
          <span className="text-cyan-300">faster with AI.</span>
        </h1>
        <p className="text-xl text-white/30 mb-10 max-w-2xl mx-auto">
          ApplyLuma tailors your CV, writes your cover letters, discovers matched jobs, and
          tracks every application — all in one place.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/register"
            className="inline-block bg-indigo-600 text-white text-base font-semibold px-8 py-3 rounded-xl hover:bg-indigo-700 transition-colors"
          >
            Start for free
          </Link>
          <Link
            to="/login"
            className="inline-block bg-white/[0.04] text-white/55 text-base font-semibold px-8 py-3 rounded-xl border border-white/10 hover:bg-white/[0.04] transition-colors"
          >
            Sign in
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-white/90 text-center mb-10">Everything you need to get hired</h2>
        <div className="grid sm:grid-cols-2 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-white/[0.04] rounded-2xl border border-white/10 p-6 hover:border-indigo-200 hover:shadow-sm transition-all"
            >
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="text-base font-semibold text-white/90 mb-2">{f.title}</h3>
              <p className="text-sm text-white/30 leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-white/90 text-center mb-10">How it works</h2>
        <div className="grid sm:grid-cols-3 gap-8">
          {STEPS.map((s) => (
            <div key={s.number} className="text-center">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgba(8,145,178,0.15)] text-cyan-300 font-bold text-lg mb-4">
                {s.number}
              </div>
              <h3 className="font-semibold text-white/90 mb-2">{s.title}</h3>
              <p className="text-sm text-white/30">{s.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="max-w-2xl mx-auto text-center bg-indigo-600 rounded-3xl px-8 py-14">
        <h2 className="text-3xl font-bold text-white mb-4">Ready to apply smarter?</h2>
        <p className="text-cyan-300 mb-8">
          Free during beta. No credit card required.
        </p>
        <Link
          to="/register"
          className="inline-block bg-white/[0.04] text-cyan-300 font-semibold px-8 py-3 rounded-xl hover:bg-[rgba(8,145,178,0.15)] transition-colors"
        >
          Create your free account
        </Link>
      </div>

    </div>
  )
}
