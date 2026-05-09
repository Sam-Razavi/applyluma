import client from '../api/client'
import type {
  AIAnalysis,
  AnalyticsEnvelope,
  CompanyInsight,
  CV,
  ExperienceLevel,
  ExperienceLevelBreakdown,
  Granularity,
  HiringPatternPoint,
  IndustryBreakdown,
  JobDescription,
  JobMarketHealth,
  JobTypeMixItem,
  LocationTrend,
  ResumeComparison,
  SalaryBySkill,
  SalaryInsightItem,
  SkillDemand,
  SkillTrend,
  TokenPair,
  User,
} from '../types'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export interface CreateJobDescriptionRequest {
  company_name: string
  job_title: string
  description: string
  url?: string
}

export const authApi = {
  login: (data: LoginRequest): Promise<TokenPair> =>
    client.post<TokenPair>('/api/v1/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest): Promise<User> =>
    client.post<User>('/api/v1/auth/register', data).then((r) => r.data),

  me: (): Promise<User> =>
    client.get<User>('/api/v1/auth/me').then((r) => r.data),
}

export const cvApi = {
  upload: (file: File, title?: string, onProgress?: (pct: number) => void): Promise<CV> => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    return client
      .post<CV>('/api/v1/cvs/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      .then((r) => r.data)
  },

  list: (): Promise<CV[]> =>
    client.get('/api/v1/cvs').then((r) => {
      const d = r.data
      return Array.isArray(d) ? d : (d.items ?? [])
    }),

  get: (cvId: string): Promise<CV> =>
    client.get<CV>(`/api/v1/cvs/${cvId}`).then((r) => r.data),

  setDefault: (cvId: string): Promise<CV> =>
    client.patch<CV>(`/api/v1/cvs/${cvId}/set-default`).then((r) => r.data),

  remove: (cvId: string): Promise<void> =>
    client.delete(`/api/v1/cvs/${cvId}`).then(() => undefined),
}

export const jobApi = {
  create: (data: CreateJobDescriptionRequest): Promise<JobDescription> =>
    client.post<JobDescription>('/api/v1/job-descriptions', data).then((r) => r.data),

  list: (): Promise<JobDescription[]> =>
    client.get('/api/v1/job-descriptions').then((r) => {
      const d = r.data
      return Array.isArray(d) ? d : (d.items ?? [])
    }),

  get: (jdId: string): Promise<JobDescription> =>
    client.get<JobDescription>(`/api/v1/job-descriptions/${jdId}`).then((r) => r.data),

  remove: (jdId: string): Promise<void> =>
    client.delete(`/api/v1/job-descriptions/${jdId}`).then(() => undefined),
}

export const aiApi = {
  tailorCV: (cvId: string, jobDescriptionId: string): Promise<AIAnalysis> =>
    client
      .post<AIAnalysis>('/api/v1/ai/tailor-cv', {
        cv_id: cvId,
        job_description_id: jobDescriptionId,
      })
      .then((r) => r.data),
}

function unwrapAnalytics<T>(envelope: AnalyticsEnvelope<T>): T {
  if (!envelope.success) {
    throw new Error(envelope.error?.message ?? 'Analytics request failed')
  }
  if (envelope.data == null) {
    throw new Error('No data returned from analytics endpoint')
  }
  return envelope.data
}

export const analyticsApi = {
  trendingSkills: (limit = 20, minJobs = 1): Promise<SkillTrend[]> =>
    client
      .get<AnalyticsEnvelope<SkillTrend[]>>('/api/v1/analytics/trending-skills', {
        params: { limit, min_jobs: minJobs },
      })
      .then((r) => unwrapAnalytics(r.data)),

  salaryInsights: (params?: {
    location?: string
    job_title?: string
    experience_level?: ExperienceLevel
  }): Promise<SalaryInsightItem[]> =>
    client
      .get<AnalyticsEnvelope<SalaryInsightItem[]>>('/api/v1/analytics/salary-insights', { params })
      .then((r) => unwrapAnalytics(r.data)),

  hiringPatterns: (daysBack = 90, granularity: Granularity = 'daily'): Promise<HiringPatternPoint[]> =>
    client
      .get<AnalyticsEnvelope<HiringPatternPoint[]>>('/api/v1/analytics/hiring-patterns', {
        params: { days_back: daysBack, granularity },
      })
      .then((r) => unwrapAnalytics(r.data)),

  companyInsights: (limit = 20, location?: string): Promise<CompanyInsight[]> =>
    client
      .get<AnalyticsEnvelope<CompanyInsight[]>>('/api/v1/analytics/company-insights', {
        params: { limit, location },
      })
      .then((r) => unwrapAnalytics(r.data)),

  jobMarketHealth: (): Promise<JobMarketHealth> =>
    client
      .get<AnalyticsEnvelope<JobMarketHealth>>('/api/v1/analytics/job-market-health')
      .then((r) => unwrapAnalytics(r.data)),

  skillDemand: (limit = 20, minGrowthPct = 0): Promise<SkillDemand[]> =>
    client
      .get<AnalyticsEnvelope<SkillDemand[]>>('/api/v1/analytics/skill-demand', {
        params: { limit, min_growth_pct: minGrowthPct },
      })
      .then((r) => unwrapAnalytics(r.data)),

  locationTrends: (): Promise<LocationTrend[]> =>
    client
      .get<AnalyticsEnvelope<LocationTrend[]>>('/api/v1/analytics/location-trends')
      .then((r) => unwrapAnalytics(r.data)),

  industryBreakdown: (): Promise<IndustryBreakdown[]> =>
    client
      .get<AnalyticsEnvelope<IndustryBreakdown[]>>('/api/v1/analytics/industry-breakdown')
      .then((r) => unwrapAnalytics(r.data)),

  experienceLevels: (): Promise<ExperienceLevelBreakdown[]> =>
    client
      .get<AnalyticsEnvelope<ExperienceLevelBreakdown[]>>('/api/v1/analytics/experience-levels')
      .then((r) => unwrapAnalytics(r.data)),

  jobTypeMix: (): Promise<JobTypeMixItem[]> =>
    client
      .get<AnalyticsEnvelope<JobTypeMixItem[]>>('/api/v1/analytics/job-type-mix')
      .then((r) => unwrapAnalytics(r.data)),

  salaryBySkill: (limit = 20): Promise<SalaryBySkill[]> =>
    client
      .get<AnalyticsEnvelope<SalaryBySkill[]>>('/api/v1/analytics/salary-by-skill', {
        params: { limit },
      })
      .then((r) => unwrapAnalytics(r.data)),

  comparison: (resumeId: string): Promise<ResumeComparison> =>
    client
      .get<AnalyticsEnvelope<ResumeComparison>>('/api/v1/analytics/comparison', {
        params: { resume_id: resumeId },
      })
      .then((r) => unwrapAnalytics(r.data)),
}
