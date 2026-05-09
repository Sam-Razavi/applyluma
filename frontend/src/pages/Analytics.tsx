import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import AnalyticsHeader from '../components/analytics/AnalyticsHeader'
import ChartCard from '../components/analytics/ChartCard'
import KPICard from '../components/analytics/KPICard'
import { analyticsApi, cvApi } from '../services/api'
import { useAuthStore } from '../stores'
import type {
  CompanyInsight,
  CV,
  ExperienceLevelBreakdown,
  HiringPatternPoint,
  IndustryBreakdown,
  JobMarketHealth,
  JobTypeMixItem,
  LocationTrend,
  ResumeComparison,
  SalaryBySkill,
  SalaryInsightItem,
  SkillDemand,
  SkillTrend,
} from '../types'

const TrendingSkillsChart = lazy(() => import('../components/analytics/charts/TrendingSkillsChart'))
const SalaryInsightsChart = lazy(() => import('../components/analytics/charts/SalaryInsightsChart'))
const HiringPatternsChart = lazy(() => import('../components/analytics/charts/HiringPatternsChart'))
const CompanyInsightsChart = lazy(() => import('../components/analytics/charts/CompanyInsightsChart'))
const JobMarketHealthCard = lazy(() => import('../components/analytics/charts/JobMarketHealthCard'))
const SkillDemandChart = lazy(() => import('../components/analytics/charts/SkillDemandChart'))
const LocationTrendsChart = lazy(() => import('../components/analytics/charts/LocationTrendsChart'))
const IndustryBreakdownChart = lazy(() => import('../components/analytics/charts/IndustryBreakdownChart'))
const ExperienceLevelsChart = lazy(() => import('../components/analytics/charts/ExperienceLevelsChart'))
const JobTypeMixChart = lazy(() => import('../components/analytics/charts/JobTypeMixChart'))
const SalaryBySkillChart = lazy(() => import('../components/analytics/charts/SalaryBySkillChart'))
const ResumeComparisonChart = lazy(() => import('../components/analytics/charts/ResumeComparisonChart'))

type LoadKey =
  | 'marketHealth'
  | 'trendingSkills'
  | 'salaryInsights'
  | 'hiringPatterns'
  | 'companyInsights'
  | 'skillDemand'
  | 'locationTrends'
  | 'industryBreakdown'
  | 'experienceLevels'
  | 'jobTypeMix'
  | 'salaryBySkill'
  | 'resumeComparison'

const LOAD_KEYS: LoadKey[] = [
  'marketHealth',
  'trendingSkills',
  'salaryInsights',
  'hiringPatterns',
  'companyInsights',
  'skillDemand',
  'locationTrends',
  'industryBreakdown',
  'experienceLevels',
  'jobTypeMix',
  'salaryBySkill',
  'resumeComparison',
]

const initialLoading = LOAD_KEYS.reduce(
  (state, key) => ({ ...state, [key]: true }),
  {} as Record<LoadKey, boolean>,
)

const initialErrors = LOAD_KEYS.reduce(
  (state, key) => ({ ...state, [key]: null }),
  {} as Record<LoadKey, string | null>,
)

function chartFallback() {
  return <div className="h-64 animate-pulse rounded-lg bg-gray-100" aria-hidden="true" />
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Failed to load data'
}

interface AnalyticsSnapshot {
  marketHealth: JobMarketHealth | null
  trendingSkills: SkillTrend[]
  salaryInsights: SalaryInsightItem[]
  hiringPatterns: HiringPatternPoint[]
  companyInsights: CompanyInsight[]
  skillDemand: SkillDemand[]
  locationTrends: LocationTrend[]
  industryBreakdown: IndustryBreakdown[]
  experienceLevels: ExperienceLevelBreakdown[]
  jobTypeMix: JobTypeMixItem[]
  salaryBySkill: SalaryBySkill[]
  cvs: CV[]
  selectedResumeId: string
  resumeComparison: ResumeComparison | null
  errors: Record<LoadKey, string | null>
}

interface ResumeSnapshot {
  cvs: CV[]
  selectedResumeId: string
  resumeComparison: ResumeComparison | null
  error: string | null
}

const INITIAL_ANALYTICS_DEDUPE_MS = 10_000

let initialAnalyticsLoad:
  | {
      createdAt: number
      promise: Promise<AnalyticsSnapshot>
    }
  | null = null

let initialResumeLoad:
  | {
      tokenKey: string
      createdAt: number
      promise: Promise<ResumeSnapshot>
    }
  | null = null

function emptyAnalyticsSnapshot(): AnalyticsSnapshot {
  return {
    marketHealth: null,
    trendingSkills: [],
    salaryInsights: [],
    hiringPatterns: [],
    companyInsights: [],
    skillDemand: [],
    locationTrends: [],
    industryBreakdown: [],
    experienceLevels: [],
    jobTypeMix: [],
    salaryBySkill: [],
    cvs: [],
    selectedResumeId: '',
    resumeComparison: null,
    errors: { ...initialErrors },
  }
}

function applySettledResult<T>(
  result: PromiseSettledResult<T>,
  key: LoadKey,
  snapshot: AnalyticsSnapshot,
  applyValue: (value: T) => void,
) {
  if (result.status === 'fulfilled') {
    applyValue(result.value)
    snapshot.errors[key] = null
    return
  }

  snapshot.errors[key] = getErrorMessage(result.reason)
}

async function fetchInitialAnalyticsSnapshot(): Promise<AnalyticsSnapshot> {
  const snapshot = emptyAnalyticsSnapshot()

  const [
    marketHealthResult,
    trendingSkillsResult,
    salaryInsightsResult,
    hiringPatternsResult,
    companyInsightsResult,
    skillDemandResult,
    locationTrendsResult,
    industryBreakdownResult,
    experienceLevelsResult,
    jobTypeMixResult,
    salaryBySkillResult,
  ] = await Promise.allSettled([
    analyticsApi.jobMarketHealth(),
    analyticsApi.trendingSkills(20, 1),
    analyticsApi.salaryInsights(),
    analyticsApi.hiringPatterns(30, 'daily'),
    analyticsApi.companyInsights(20),
    analyticsApi.skillDemand(20, 0),
    analyticsApi.locationTrends(),
    analyticsApi.industryBreakdown(),
    analyticsApi.experienceLevels(),
    analyticsApi.jobTypeMix(),
    analyticsApi.salaryBySkill(20),
  ])

  applySettledResult(marketHealthResult, 'marketHealth', snapshot, (value) => {
    snapshot.marketHealth = value
  })
  applySettledResult(trendingSkillsResult, 'trendingSkills', snapshot, (value) => {
    snapshot.trendingSkills = value
  })
  applySettledResult(salaryInsightsResult, 'salaryInsights', snapshot, (value) => {
    snapshot.salaryInsights = value
  })
  applySettledResult(hiringPatternsResult, 'hiringPatterns', snapshot, (value) => {
    snapshot.hiringPatterns = value
  })
  applySettledResult(companyInsightsResult, 'companyInsights', snapshot, (value) => {
    snapshot.companyInsights = value
  })
  applySettledResult(skillDemandResult, 'skillDemand', snapshot, (value) => {
    snapshot.skillDemand = value
  })
  applySettledResult(locationTrendsResult, 'locationTrends', snapshot, (value) => {
    snapshot.locationTrends = value
  })
  applySettledResult(industryBreakdownResult, 'industryBreakdown', snapshot, (value) => {
    snapshot.industryBreakdown = value
  })
  applySettledResult(experienceLevelsResult, 'experienceLevels', snapshot, (value) => {
    snapshot.experienceLevels = value
  })
  applySettledResult(jobTypeMixResult, 'jobTypeMix', snapshot, (value) => {
    snapshot.jobTypeMix = value
  })
  applySettledResult(salaryBySkillResult, 'salaryBySkill', snapshot, (value) => {
    snapshot.salaryBySkill = value
  })

  return snapshot
}

function getInitialAnalyticsSnapshot(): Promise<AnalyticsSnapshot> {
  const now = Date.now()

  if (
    initialAnalyticsLoad &&
    now - initialAnalyticsLoad.createdAt < INITIAL_ANALYTICS_DEDUPE_MS
  ) {
    return initialAnalyticsLoad.promise
  }

  initialAnalyticsLoad = {
    createdAt: now,
    promise: fetchInitialAnalyticsSnapshot(),
  }

  return initialAnalyticsLoad.promise
}

async function fetchInitialResumeSnapshot(): Promise<ResumeSnapshot> {
  try {
    const nextCvs = await cvApi.list()
    const targetResumeId = nextCvs.find((cv) => cv.is_default)?.id ?? nextCvs[0]?.id ?? ''

    return {
      cvs: nextCvs,
      selectedResumeId: targetResumeId,
      resumeComparison: targetResumeId ? await analyticsApi.comparison(targetResumeId) : null,
      error: null,
    }
  } catch (error) {
    return {
      cvs: [],
      selectedResumeId: '',
      resumeComparison: null,
      error: getErrorMessage(error),
    }
  }
}

function getInitialResumeSnapshot(token: string): Promise<ResumeSnapshot> {
  const now = Date.now()

  if (
    initialResumeLoad &&
    initialResumeLoad.tokenKey === token &&
    now - initialResumeLoad.createdAt < INITIAL_ANALYTICS_DEDUPE_MS
  ) {
    return initialResumeLoad.promise
  }

  initialResumeLoad = {
    tokenKey: token,
    createdAt: now,
    promise: fetchInitialResumeSnapshot(),
  }

  return initialResumeLoad.promise
}

export default function Analytics() {
  const { token } = useAuthStore()

  const [loading, setLoading] = useState<Record<LoadKey, boolean>>(initialLoading)
  const [errors, setErrors] = useState<Record<LoadKey, string | null>>(initialErrors)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const [marketHealth, setMarketHealth] = useState<JobMarketHealth | null>(null)
  const [trendingSkills, setTrendingSkills] = useState<SkillTrend[]>([])
  const [salaryInsights, setSalaryInsights] = useState<SalaryInsightItem[]>([])
  const [hiringPatterns, setHiringPatterns] = useState<HiringPatternPoint[]>([])
  const [companyInsights, setCompanyInsights] = useState<CompanyInsight[]>([])
  const [skillDemand, setSkillDemand] = useState<SkillDemand[]>([])
  const [locationTrends, setLocationTrends] = useState<LocationTrend[]>([])
  const [industryBreakdown, setIndustryBreakdown] = useState<IndustryBreakdown[]>([])
  const [experienceLevels, setExperienceLevels] = useState<ExperienceLevelBreakdown[]>([])
  const [jobTypeMix, setJobTypeMix] = useState<JobTypeMixItem[]>([])
  const [salaryBySkill, setSalaryBySkill] = useState<SalaryBySkill[]>([])
  const [cvs, setCvs] = useState<CV[]>([])
  const [selectedResumeId, setSelectedResumeId] = useState('')
  const [resumeComparison, setResumeComparison] = useState<ResumeComparison | null>(null)

  const setEndpointLoading = useCallback((key: LoadKey, value: boolean) => {
    setLoading((prev) => ({ ...prev, [key]: value }))
  }, [])

  const setEndpointError = useCallback((key: LoadKey, value: string | null) => {
    setErrors((prev) => ({ ...prev, [key]: value }))
  }, [])

  const loadMarketHealth = useCallback(async () => {
    setEndpointLoading('marketHealth', true)
    try {
      setMarketHealth(await analyticsApi.jobMarketHealth())
      setEndpointError('marketHealth', null)
    } catch (error) {
      setEndpointError('marketHealth', getErrorMessage(error))
    } finally {
      setEndpointLoading('marketHealth', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadTrendingSkills = useCallback(async () => {
    setEndpointLoading('trendingSkills', true)
    try {
      setTrendingSkills(await analyticsApi.trendingSkills(20, 1))
      setEndpointError('trendingSkills', null)
    } catch (error) {
      setEndpointError('trendingSkills', getErrorMessage(error))
    } finally {
      setEndpointLoading('trendingSkills', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadSalaryInsights = useCallback(async () => {
    setEndpointLoading('salaryInsights', true)
    try {
      setSalaryInsights(await analyticsApi.salaryInsights())
      setEndpointError('salaryInsights', null)
    } catch (error) {
      setEndpointError('salaryInsights', getErrorMessage(error))
    } finally {
      setEndpointLoading('salaryInsights', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadHiringPatterns = useCallback(async () => {
    setEndpointLoading('hiringPatterns', true)
    try {
      setHiringPatterns(await analyticsApi.hiringPatterns(30, 'daily'))
      setEndpointError('hiringPatterns', null)
    } catch (error) {
      setEndpointError('hiringPatterns', getErrorMessage(error))
    } finally {
      setEndpointLoading('hiringPatterns', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadCompanyInsights = useCallback(async () => {
    setEndpointLoading('companyInsights', true)
    try {
      setCompanyInsights(await analyticsApi.companyInsights(20))
      setEndpointError('companyInsights', null)
    } catch (error) {
      setEndpointError('companyInsights', getErrorMessage(error))
    } finally {
      setEndpointLoading('companyInsights', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadSkillDemand = useCallback(async () => {
    setEndpointLoading('skillDemand', true)
    try {
      setSkillDemand(await analyticsApi.skillDemand(20, 0))
      setEndpointError('skillDemand', null)
    } catch (error) {
      setEndpointError('skillDemand', getErrorMessage(error))
    } finally {
      setEndpointLoading('skillDemand', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadLocationTrends = useCallback(async () => {
    setEndpointLoading('locationTrends', true)
    try {
      setLocationTrends(await analyticsApi.locationTrends())
      setEndpointError('locationTrends', null)
    } catch (error) {
      setEndpointError('locationTrends', getErrorMessage(error))
    } finally {
      setEndpointLoading('locationTrends', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadIndustryBreakdown = useCallback(async () => {
    setEndpointLoading('industryBreakdown', true)
    try {
      setIndustryBreakdown(await analyticsApi.industryBreakdown())
      setEndpointError('industryBreakdown', null)
    } catch (error) {
      setEndpointError('industryBreakdown', getErrorMessage(error))
    } finally {
      setEndpointLoading('industryBreakdown', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadExperienceLevels = useCallback(async () => {
    setEndpointLoading('experienceLevels', true)
    try {
      setExperienceLevels(await analyticsApi.experienceLevels())
      setEndpointError('experienceLevels', null)
    } catch (error) {
      setEndpointError('experienceLevels', getErrorMessage(error))
    } finally {
      setEndpointLoading('experienceLevels', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadJobTypeMix = useCallback(async () => {
    setEndpointLoading('jobTypeMix', true)
    try {
      setJobTypeMix(await analyticsApi.jobTypeMix())
      setEndpointError('jobTypeMix', null)
    } catch (error) {
      setEndpointError('jobTypeMix', getErrorMessage(error))
    } finally {
      setEndpointLoading('jobTypeMix', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadSalaryBySkill = useCallback(async () => {
    setEndpointLoading('salaryBySkill', true)
    try {
      setSalaryBySkill(await analyticsApi.salaryBySkill(20))
      setEndpointError('salaryBySkill', null)
    } catch (error) {
      setEndpointError('salaryBySkill', getErrorMessage(error))
    } finally {
      setEndpointLoading('salaryBySkill', false)
    }
  }, [setEndpointError, setEndpointLoading])

  const loadResumeComparison = useCallback(
    async (resumeId?: string) => {
      if (!token) {
        setEndpointLoading('resumeComparison', false)
        return
      }

      setEndpointLoading('resumeComparison', true)
      try {
        const nextCvs = await cvApi.list()
        setCvs(nextCvs)

        let targetResumeId = resumeId ?? ''
        if (!targetResumeId) {
          targetResumeId = nextCvs.find((cv) => cv.is_default)?.id ?? nextCvs[0]?.id ?? ''
          setSelectedResumeId(targetResumeId)
        }

        setResumeComparison(targetResumeId ? await analyticsApi.comparison(targetResumeId) : null)
        setEndpointError('resumeComparison', null)
      } catch (error) {
        setEndpointError('resumeComparison', getErrorMessage(error))
      } finally {
        setEndpointLoading('resumeComparison', false)
      }
    },
    [setEndpointError, setEndpointLoading, token],
  )

  const loadAllData = useCallback(async () => {
    setRefreshing(true)

    await Promise.allSettled([
      loadMarketHealth(),
      loadTrendingSkills(),
      loadSalaryInsights(),
      loadHiringPatterns(),
      loadCompanyInsights(),
      loadSkillDemand(),
      loadLocationTrends(),
      loadIndustryBreakdown(),
      loadExperienceLevels(),
      loadJobTypeMix(),
      loadSalaryBySkill(),
      loadResumeComparison(),
    ])

    setLastRefresh(new Date())
    setRefreshing(false)
  }, [
    loadCompanyInsights,
    loadExperienceLevels,
    loadHiringPatterns,
    loadIndustryBreakdown,
    loadJobTypeMix,
    loadLocationTrends,
    loadMarketHealth,
    loadResumeComparison,
    loadSalaryBySkill,
    loadSalaryInsights,
    loadSkillDemand,
    loadTrendingSkills,
  ])

  const applyAnalyticsSnapshot = useCallback((snapshot: AnalyticsSnapshot) => {
    setMarketHealth(snapshot.marketHealth)
    setTrendingSkills(snapshot.trendingSkills)
    setSalaryInsights(snapshot.salaryInsights)
    setHiringPatterns(snapshot.hiringPatterns)
    setCompanyInsights(snapshot.companyInsights)
    setSkillDemand(snapshot.skillDemand)
    setLocationTrends(snapshot.locationTrends)
    setIndustryBreakdown(snapshot.industryBreakdown)
    setExperienceLevels(snapshot.experienceLevels)
    setJobTypeMix(snapshot.jobTypeMix)
    setSalaryBySkill(snapshot.salaryBySkill)
    setErrors((prev) => ({ ...snapshot.errors, resumeComparison: prev.resumeComparison }))
    setLoading((prev) =>
      LOAD_KEYS.reduce(
        (state, key) => ({ ...state, [key]: key === 'resumeComparison' ? prev.resumeComparison : false }),
        {} as Record<LoadKey, boolean>,
      ),
    )
    setLastRefresh(new Date())
  }, [])

  useEffect(() => {
    document.title = 'Market Intelligence | ApplyLuma'
  }, [])

  useEffect(() => {
    let isMounted = true

    void getInitialAnalyticsSnapshot()
      .then((snapshot) => {
        if (isMounted) {
          applyAnalyticsSnapshot(snapshot)
        }
      })
      .catch((error) => {
        if (!isMounted) return

        console.error('Failed to load analytics:', error)
        setErrors(
          LOAD_KEYS.reduce(
            (state, key) => ({ ...state, [key]: getErrorMessage(error) }),
            {} as Record<LoadKey, string | null>,
          ),
        )
        setLoading(
          LOAD_KEYS.reduce(
            (state, key) => ({ ...state, [key]: false }),
            {} as Record<LoadKey, boolean>,
          ),
        )
      })

    return () => {
      isMounted = false
    }
  }, [applyAnalyticsSnapshot])

  useEffect(() => {
    let isMounted = true

    if (!token) {
      setEndpointLoading('resumeComparison', false)
      return () => {
        isMounted = false
      }
    }

    setEndpointLoading('resumeComparison', true)

    void getInitialResumeSnapshot(token)
      .then((snapshot) => {
        if (!isMounted) return

        setCvs(snapshot.cvs)
        setSelectedResumeId(snapshot.selectedResumeId)
        setResumeComparison(snapshot.resumeComparison)
        setEndpointError('resumeComparison', snapshot.error)
      })
      .finally(() => {
        if (isMounted) {
          setEndpointLoading('resumeComparison', false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [setEndpointError, setEndpointLoading, token])

  const handleResumeChange = (resumeId: string) => {
    setSelectedResumeId(resumeId)
    setResumeComparison(null)
    void loadResumeComparison(resumeId)
  }

  return (
    <div className="space-y-6">
      <AnalyticsHeader onRefresh={loadAllData} refreshing={refreshing} lastRefresh={lastRefresh} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <KPICard
          title="Total Jobs"
          value={marketHealth?.total_jobs}
          icon="briefcase"
          loading={loading.marketHealth}
          error={errors.marketHealth}
        />
        <KPICard
          title="Avg Salary"
          value={marketHealth?.avg_salary_midpoint}
          format="currency"
          icon="dollar"
          loading={loading.marketHealth}
          error={errors.marketHealth}
        />
        <KPICard
          title="Companies"
          value={marketHealth?.unique_companies}
          icon="building"
          loading={loading.marketHealth}
          error={errors.marketHealth}
        />
        <KPICard
          title="Remote"
          value={marketHealth?.remote_percentage}
          format="percentage"
          icon="home"
          loading={loading.marketHealth}
          error={errors.marketHealth}
        />
        <KPICard
          title="Growth"
          value={skillDemand[0]?.trending_score_pct ?? null}
          format="percentage"
          trend={skillDemand[0]?.trending_score_pct ?? null}
          icon="trending-up"
          loading={loading.skillDemand}
          error={errors.skillDemand}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ChartCard
          title="Trending Skills"
          subtitle="Top in-demand skills by job count"
          loading={loading.trendingSkills}
          error={errors.trendingSkills}
          empty={trendingSkills.length === 0}
          onRetry={loadTrendingSkills}
        >
          <Suspense fallback={chartFallback()}>
            <TrendingSkillsChart data={trendingSkills} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Salary Insights"
          subtitle="Salary percentiles by market segment"
          loading={loading.salaryInsights}
          error={errors.salaryInsights}
          empty={salaryInsights.length === 0}
          onRetry={loadSalaryInsights}
        >
          <Suspense fallback={chartFallback()}>
            <SalaryInsightsChart data={salaryInsights} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Top Companies"
          subtitle="Companies hiring most"
          loading={loading.companyInsights}
          error={errors.companyInsights}
          empty={companyInsights.length === 0}
          onRetry={loadCompanyInsights}
        >
          <Suspense fallback={chartFallback()}>
            <CompanyInsightsChart data={companyInsights} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Hiring Patterns"
          subtitle="Job postings over the last 30 days"
          className="lg:col-span-2"
          loading={loading.hiringPatterns}
          error={errors.hiringPatterns}
          empty={hiringPatterns.length === 0}
          onRetry={loadHiringPatterns}
        >
          <Suspense fallback={chartFallback()}>
            <HiringPatternsChart data={hiringPatterns} />
          </Suspense>
        </ChartCard>

        <Suspense fallback={chartFallback()}>
          <JobMarketHealthCard data={marketHealth} loading={loading.marketHealth} error={errors.marketHealth} />
        </Suspense>

        <ChartCard
          title="Skill Demand Growth"
          subtitle="This week vs last week"
          loading={loading.skillDemand}
          error={errors.skillDemand}
          empty={skillDemand.length === 0}
          onRetry={loadSkillDemand}
        >
          <Suspense fallback={chartFallback()}>
            <SkillDemandChart data={skillDemand} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Location Trends"
          subtitle="Geographic distribution"
          loading={loading.locationTrends}
          error={errors.locationTrends}
          empty={locationTrends.length === 0}
          onRetry={loadLocationTrends}
        >
          <Suspense fallback={chartFallback()}>
            <LocationTrendsChart data={locationTrends} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Industry Breakdown"
          subtitle="Jobs by derived sector"
          loading={loading.industryBreakdown}
          error={errors.industryBreakdown}
          empty={industryBreakdown.length === 0}
          onRetry={loadIndustryBreakdown}
        >
          <Suspense fallback={chartFallback()}>
            <IndustryBreakdownChart data={industryBreakdown} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Experience Levels"
          subtitle="Jobs by seniority"
          loading={loading.experienceLevels}
          error={errors.experienceLevels}
          empty={experienceLevels.length === 0}
          onRetry={loadExperienceLevels}
        >
          <Suspense fallback={chartFallback()}>
            <ExperienceLevelsChart data={experienceLevels} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Job Type Mix"
          subtitle="Employment type and remote status"
          loading={loading.jobTypeMix}
          error={errors.jobTypeMix}
          empty={jobTypeMix.length === 0}
          onRetry={loadJobTypeMix}
        >
          <Suspense fallback={chartFallback()}>
            <JobTypeMixChart data={jobTypeMix} />
          </Suspense>
        </ChartCard>

        <ChartCard
          title="Salary by Skill"
          subtitle="Top paying skills"
          loading={loading.salaryBySkill}
          error={errors.salaryBySkill}
          empty={salaryBySkill.length === 0}
          onRetry={loadSalaryBySkill}
        >
          <Suspense fallback={chartFallback()}>
            <SalaryBySkillChart data={salaryBySkill} />
          </Suspense>
        </ChartCard>

        {token && (
          <ChartCard
            title="Your Resume vs Market"
            subtitle="Skill alignment and market coverage"
            className="lg:col-span-3"
            loading={loading.resumeComparison}
            error={errors.resumeComparison}
            onRetry={() => loadResumeComparison(selectedResumeId)}
          >
            {cvs.length > 0 && (
              <div className="mb-4 max-w-sm">
                <label htmlFor="analytics-resume" className="mb-1 block text-xs font-medium text-gray-600">
                  Resume
                </label>
                <select
                  id="analytics-resume"
                  value={selectedResumeId}
                  onChange={(event) => handleResumeChange(event.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                >
                  {cvs.map((cv) => (
                    <option key={cv.id} value={cv.id}>
                      {cv.title || cv.filename}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <Suspense fallback={chartFallback()}>
              <ResumeComparisonChart data={resumeComparison} />
            </Suspense>
          </ChartCard>
        )}
      </div>
    </div>
  )
}
