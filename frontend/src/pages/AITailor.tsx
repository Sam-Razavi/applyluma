import { useEffect, useState } from 'react'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  SparklesIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid'
import toast from 'react-hot-toast'
import { cvApi, jobApi, aiApi } from '../services/api'
import type { CV, JobDescription, AIAnalysis } from '../types'

function ScoreRing({ score }: { score: number }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ

  const color =
    score >= 80 ? '#16a34a' : score >= 60 ? '#ca8a04' : score >= 40 ? '#ea580c' : '#dc2626'

  const label =
    score >= 80
      ? 'Excellent match'
      : score >= 60
      ? 'Good match'
      : score >= 40
      ? 'Fair match'
      : 'Needs work'

  const labelColor =
    score >= 80
      ? 'text-green-600'
      : score >= 60
      ? 'text-yellow-600'
      : score >= 40
      ? 'text-orange-600'
      : 'text-red-600'

  const bgColor =
    score >= 80
      ? 'bg-green-50'
      : score >= 60
      ? 'bg-yellow-50'
      : score >= 40
      ? 'bg-orange-50'
      : 'bg-red-50'

  return (
    <div className={`flex flex-col items-center justify-center rounded-2xl p-8 ${bgColor}`}>
      <div className="relative">
        <svg width="128" height="128" className="-rotate-90">
          <circle cx="64" cy="64" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
          <circle
            cx="64"
            cy="64"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={`${filled} ${circ}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-900">{score}</span>
          <span className="text-xs text-gray-500 font-medium">/ 100</span>
        </div>
      </div>
      <p className={`mt-3 text-sm font-semibold ${labelColor}`}>{label}</p>
    </div>
  )
}

function CollapsibleSection({
  title,
  icon,
  iconClass,
  children,
  defaultOpen = true,
}: {
  title: string
  icon: React.ReactNode
  iconClass: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${iconClass}`}>
            {icon}
          </div>
          <span className="text-sm font-semibold text-gray-900">{title}</span>
        </div>
        {open ? (
          <ChevronUpIcon className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDownIcon className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {open && <div className="px-6 pb-5 border-t border-gray-100">{children}</div>}
    </div>
  )
}

export default function AITailor() {
  const [cvs, setCvs] = useState<CV[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [loadingData, setLoadingData] = useState(true)

  const [selectedCvId, setSelectedCvId] = useState('')
  const [selectedJobId, setSelectedJobId] = useState('')

  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AIAnalysis | null>(null)
  const [fullAnalysisOpen, setFullAnalysisOpen] = useState(false)

  useEffect(() => {
    Promise.all([cvApi.list(), jobApi.list()])
      .then(([c, j]) => {
        setCvs(c)
        setJobs(j)
        if (c.length === 1) setSelectedCvId(c[0].id)
        if (j.length === 1) setSelectedJobId(j[0].id)
      })
      .catch(() => toast.error('Failed to load your CVs and jobs'))
      .finally(() => setLoadingData(false))
  }, [])

  async function handleAnalyze() {
    if (!selectedCvId || !selectedJobId) return
    setAnalyzing(true)
    setResult(null)
    try {
      const analysis = await aiApi.tailorCV(selectedCvId, selectedJobId)
      setResult(analysis)
      toast.success('Analysis complete!')
    } catch {
      toast.error('Analysis failed. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  function reset() {
    setResult(null)
    setFullAnalysisOpen(false)
  }

  const selectedCv = cvs.find((c) => c.id === selectedCvId)
  const selectedJob = jobs.find((j) => j.id === selectedJobId)
  const canAnalyze = !!selectedCvId && !!selectedJobId && !analyzing

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <SparklesIcon className="h-7 w-7 text-brand-500" />
          AI Tailor
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Match your CV to a job description and get actionable AI-powered recommendations.
        </p>
      </div>

      {/* Selection card */}
      {!result && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-6">
          <h2 className="text-sm font-semibold text-gray-700">Select your CV and target job</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* CV selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                Your CV
              </label>
              {loadingData ? (
                <div className="h-10 bg-gray-100 rounded-lg animate-pulse" />
              ) : cvs.length === 0 ? (
                <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-gray-300 text-sm text-gray-400">
                  No CVs found —{' '}
                  <a href="/cvs" className="text-brand-500 hover:underline">
                    upload one
                  </a>
                </div>
              ) : (
                <select
                  value={selectedCvId}
                  onChange={(e) => setSelectedCvId(e.target.value)}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                >
                  <option value="">Choose a CV…</option>
                  {cvs.map((cv) => (
                    <option key={cv.id} value={cv.id}>
                      {cv.title}
                      {cv.is_default ? ' (default)' : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Job selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                Target Job
              </label>
              {loadingData ? (
                <div className="h-10 bg-gray-100 rounded-lg animate-pulse" />
              ) : jobs.length === 0 ? (
                <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-gray-300 text-sm text-gray-400">
                  No jobs found —{' '}
                  <a href="/jobs" className="text-brand-500 hover:underline">
                    add one
                  </a>
                </div>
              ) : (
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                >
                  <option value="">Choose a job…</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.job_title} @ {j.company_name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Selection summary */}
          {(selectedCv || selectedJob) && (
            <div className="flex flex-wrap gap-2">
              {selectedCv && (
                <span className="inline-flex items-center gap-1.5 text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">
                  <CheckCircleSolid className="h-3.5 w-3.5 text-blue-500" />
                  {selectedCv.title}
                </span>
              )}
              {selectedJob && (
                <span className="inline-flex items-center gap-1.5 text-xs bg-violet-50 text-violet-700 px-2.5 py-1 rounded-full font-medium">
                  <CheckCircleSolid className="h-3.5 w-3.5 text-violet-500" />
                  {selectedJob.job_title} @ {selectedJob.company_name}
                </span>
              )}
            </div>
          )}

          {/* Analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={!canAnalyze}
            className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm px-6 py-2.5 rounded-xl transition-colors"
          >
            {analyzing ? (
              <>
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
                Analyzing your CV…
              </>
            ) : (
              <>
                <SparklesIcon className="h-4 w-4" />
                Analyze Match
              </>
            )}
          </button>

          {analyzing && (
            <p className="text-xs text-gray-400">
              This usually takes 5–15 seconds. Hang tight while our AI reviews your profile…
            </p>
          )}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Context banner */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="text-sm text-gray-500">
              <span className="font-medium text-gray-700">{selectedCv?.title}</span>
              {' vs '}
              <span className="font-medium text-gray-700">
                {selectedJob?.job_title} @ {selectedJob?.company_name}
              </span>
            </div>
            <button
              onClick={reset}
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Run another analysis
            </button>
          </div>

          {/* Score + overview row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <ScoreRing score={result.match_score} />

            {/* Quick stats */}
            <div className="sm:col-span-2 grid grid-cols-3 gap-3">
              <div className="bg-green-50 rounded-2xl p-4 flex flex-col items-center justify-center text-center">
                <CheckCircleIcon className="h-7 w-7 text-green-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{result.strengths.length}</p>
                <p className="text-xs text-green-700 font-medium mt-0.5">Strengths</p>
              </div>
              <div className="bg-orange-50 rounded-2xl p-4 flex flex-col items-center justify-center text-center">
                <ExclamationTriangleIcon className="h-7 w-7 text-orange-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{result.gaps.length}</p>
                <p className="text-xs text-orange-700 font-medium mt-0.5">Gaps</p>
              </div>
              <div className="bg-brand-50 rounded-2xl p-4 flex flex-col items-center justify-center text-center">
                <LightBulbIcon className="h-7 w-7 text-brand-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{result.recommendations.length}</p>
                <p className="text-xs text-brand-700 font-medium mt-0.5">Tips</p>
              </div>
            </div>
          </div>

          {/* Strengths */}
          <CollapsibleSection
            title={`Strengths (${result.strengths.length})`}
            icon={<CheckCircleIcon className="h-4 w-4 text-green-600" />}
            iconClass="bg-green-100"
          >
            <ul className="mt-4 space-y-2.5">
              {result.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-3">
                  <CheckCircleSolid className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{s}</span>
                </li>
              ))}
            </ul>
          </CollapsibleSection>

          {/* Gaps */}
          <CollapsibleSection
            title={`Gaps to Address (${result.gaps.length})`}
            icon={<ExclamationTriangleIcon className="h-4 w-4 text-orange-600" />}
            iconClass="bg-orange-100"
          >
            <ul className="mt-4 space-y-2.5">
              {result.gaps.map((g, i) => (
                <li key={i} className="flex items-start gap-3">
                  <ExclamationTriangleIcon className="h-4 w-4 text-orange-500 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{g}</span>
                </li>
              ))}
            </ul>
          </CollapsibleSection>

          {/* Recommendations */}
          <CollapsibleSection
            title={`Recommendations (${result.recommendations.length})`}
            icon={<LightBulbIcon className="h-4 w-4 text-brand-600" />}
            iconClass="bg-brand-100"
          >
            <ol className="mt-4 space-y-3">
              {result.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-5 w-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-sm text-gray-700">{rec}</span>
                </li>
              ))}
            </ol>
          </CollapsibleSection>

          {/* Full analysis */}
          {result.full_analysis && (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              <button
                onClick={() => setFullAnalysisOpen((o) => !o)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-gray-100 flex items-center justify-center">
                    <SparklesIcon className="h-4 w-4 text-gray-500" />
                  </div>
                  <span className="text-sm font-semibold text-gray-900">Full AI Analysis</span>
                </div>
                {fullAnalysisOpen ? (
                  <ChevronUpIcon className="h-4 w-4 text-gray-400" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                )}
              </button>
              {fullAnalysisOpen && (
                <div className="px-6 pb-6 border-t border-gray-100">
                  <p className="mt-4 text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                    {result.full_analysis}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
