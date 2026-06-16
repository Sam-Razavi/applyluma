import client from '../api/client'

export interface AdminOverviewStats {
  total_users: number
  premium_users: number
  admin_users: number
  new_users_this_week: number
  total_cvs: number
  total_job_descriptions: number
  total_applications: number
  total_tailor_jobs: number
  tailor_jobs_complete: number
  tailor_jobs_failed: number
  tailor_jobs_pending: number
  total_cover_letters: number
}

export interface AdminUserRow {
  id: string
  email: string
  full_name: string | null
  role: 'user' | 'premium' | 'admin'
  is_active: boolean
  is_verified: boolean
  subscription_status: string | null
  created_at: string
}

export interface AdminUserListResponse {
  items: AdminUserRow[]
  total: number
  page: number
  size: number
}

export interface PipelineStage {
  name: string
  count: number
  last_run: string | null
  healthy: boolean
}

export interface SourceHealth {
  source: string
  count: number
  last_run: string | null
  healthy: boolean
}

export interface PipelineHealth {
  raw_job_postings: PipelineStage
  extracted_keywords: PipelineStage
  job_market_metrics: PipelineStage
  sources: SourceHealth[]
}

export interface JobsOverTimePoint {
  date: string
  count: number
}

export interface JobsBySourceItem {
  source: string
  count: number
}

export interface TopSkillItem {
  skill: string
  count: number
}

export interface TopCompanyItem {
  company: string
  count: number
}

export interface PipelineMetrics {
  metric_date: string | null
  total_jobs_scraped: number | null
  remote_percentage: number | null
  top_skills: TopSkillItem[]
  top_companies: TopCompanyItem[]
}

export const adminApi = {
  getStats(): Promise<AdminOverviewStats> {
    return client.get('/api/v1/admin/stats').then((r) => r.data)
  },

  listUsers(params: {
    search?: string
    role?: string
    page?: number
    size?: number
  }): Promise<AdminUserListResponse> {
    return client.get('/api/v1/admin/users', { params }).then((r) => r.data)
  },

  updateRole(userId: string, role: string): Promise<AdminUserRow> {
    return client.patch(`/api/v1/admin/users/${userId}/role`, { role }).then((r) => r.data)
  },

  updateActive(userId: string, is_active: boolean): Promise<AdminUserRow> {
    return client.patch(`/api/v1/admin/users/${userId}/active`, { is_active }).then((r) => r.data)
  },

  sendNotification(userId: string, title: string, body: string): Promise<void> {
    return client
      .post(`/api/v1/admin/users/${userId}/notify`, { title, body })
      .then(() => undefined)
  },

  getPipelineHealth(): Promise<PipelineHealth> {
    return client.get('/api/v1/admin/pipeline/health').then((r) => r.data)
  },

  getJobsOverTime(): Promise<JobsOverTimePoint[]> {
    return client.get('/api/v1/admin/pipeline/jobs-over-time').then((r) => r.data)
  },

  getJobsBySource(): Promise<JobsBySourceItem[]> {
    return client.get('/api/v1/admin/pipeline/jobs-by-source').then((r) => r.data)
  },

  getPipelineMetrics(): Promise<PipelineMetrics> {
    return client.get('/api/v1/admin/pipeline/metrics').then((r) => r.data)
  },
}
