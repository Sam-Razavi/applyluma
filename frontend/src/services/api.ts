import client from '../api/client'
import type { TokenPair, User, CV, JobDescription, AIAnalysis } from '../types'

// ── Analytics types ───────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_jobs: number
  remote_percentage: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  top_skill: string | null
  last_updated: string | null
}

export interface CompanyStat {
  company: string
  job_count: number
}

export interface SkillStat {
  skill: string
  mention_count: number
  trend: 'up' | 'down' | 'stable'
}

export interface DailyJobCount {
  date: string
  job_count: number
}

export interface RecentJob {
  id: string
  title: string
  company: string
  location: string | null
  url: string
  remote_allowed: boolean
  employment_type: string | null
  extracted_skills: string[] | null
  scraped_at: string
}

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

// ── Analytics API ─────────────────────────────────────────────────────────────

export const analyticsApi = {
  overview: (): Promise<AnalyticsOverview> =>
    client.get<AnalyticsOverview>('/api/v1/analytics/overview').then((r) => r.data),

  topCompanies: (limit = 10): Promise<CompanyStat[]> =>
    client
      .get<CompanyStat[]>('/api/v1/analytics/top-companies', { params: { limit } })
      .then((r) => r.data),

  topSkills: (limit = 10): Promise<SkillStat[]> =>
    client
      .get<SkillStat[]>('/api/v1/analytics/top-skills', { params: { limit } })
      .then((r) => r.data),

  jobsOverTime: (days = 30): Promise<DailyJobCount[]> =>
    client
      .get<DailyJobCount[]>('/api/v1/analytics/jobs-over-time', { params: { days } })
      .then((r) => r.data),

  recentJobs: (limit = 20): Promise<RecentJob[]> =>
    client
      .get<RecentJob[]>('/api/v1/analytics/recent-jobs', { params: { limit } })
      .then((r) => r.data),
}
