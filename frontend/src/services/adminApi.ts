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
  last_login_at: string | null
  login_count: number
}

export interface AdminUserActivitySummary {
  cvs: number
  tailored_cvs: number
  job_descriptions: number
  applications: number
  saved_jobs: number
  tailor_jobs: number
  tailor_jobs_failed: number
  cover_letters: number
  cover_letters_failed: number
  notifications: number
  unread_notifications: number
}

export interface AdminUserAiCosts {
  last_30_days_usd: number
  all_time_usd: number
  all_time_calls: number
}

export interface AdminUserProfile extends AdminUserRow {
  auth_provider: string | null
  avatar_url: string | null
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  subscription_ends_at: string | null
  updated_at: string
  daily_tailor_limit_override: number | null
  activity: AdminUserActivitySummary
  ai_costs: AdminUserAiCosts
}

export interface AdminActivityEvent {
  type: string
  title: string
  status: string | null
  timestamp: string
  ref_id: string | null
}

export interface AdminUserActivityResponse {
  items: AdminActivityEvent[]
  total: number
  page: number
  size: number
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

export interface AdminAiJobRow {
  id: string
  kind: 'tailor' | 'cover_letter'
  user_id: string
  user_email: string | null
  status: string
  created_at: string
  updated_at: string
  celery_task_id: string | null
  error_message: string | null
  job_title: string | null
  company_name: string | null
  language: string | null
  intensity: string | null
  tone: string | null
  word_count: number | null
}

export interface AdminAiJobListResponse {
  items: AdminAiJobRow[]
  total: number
  page: number
  size: number
}

export interface PipelineRunLogRow {
  id: number
  pipeline_name: string
  ran_at: string
  rows_affected: number
  status: string
  error_message: string | null
}

export interface PipelineRunLogListResponse {
  items: PipelineRunLogRow[]
  total: number
  page: number
  size: number
}

export interface RawJobAdminRow {
  id: string
  source: string
  job_id_external: string
  title: string
  company: string
  location: string | null
  url: string
  salary_min: number | null
  salary_max: number | null
  employment_type: string | null
  remote_allowed: boolean
  is_remote: boolean
  is_duplicate: boolean
  application_deadline: string | null
  scraped_at: string
  keyword_count: number
  saved_count: number
  matching_score_count: number
}

export interface RawJobAdminListResponse {
  items: RawJobAdminRow[]
  total: number
  page: number
  size: number
}

export interface SystemHealthResponse {
  status: string
  version: string
  checks: Record<string, { status: string; detail: string; [key: string]: unknown }>
}

export interface AdminAuditLogRow {
  id: string
  admin_user_id: string | null
  admin_email: string | null
  target_user_id: string | null
  target_email: string | null
  action: string
  details: Record<string, unknown>
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export interface AdminAuditLogListResponse {
  items: AdminAuditLogRow[]
  total: number
  page: number
  size: number
}

export interface AdminNotificationRow {
  id: string
  user_id: string
  user_email: string | null
  type: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export interface AdminNotificationListResponse {
  items: AdminNotificationRow[]
  total: number
  page: number
  size: number
}

export interface AdminBillingSummary {
  total_users: number
  premium_users: number
  active_subscriptions: number
  canceled_subscriptions: number
  past_due_subscriptions: number
}

export interface AdminBillingUserRow {
  id: string
  email: string
  full_name: string | null
  role: 'user' | 'premium' | 'admin'
  subscription_status: string | null
  subscription_ends_at: string | null
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  created_at: string
}

export interface AdminBillingUserListResponse {
  items: AdminBillingUserRow[]
  total: number
  page: number
  size: number
  summary: AdminBillingSummary
}

export interface ContactSubmissionRow {
  id: string
  user_id: string | null
  name: string
  email: string
  subject: string
  message: string
  category: string
  source: string
  status: string
  remote_ip: string | null
  user_agent: string | null
  created_at: string
  updated_at: string
}

export interface ContactSubmissionListResponse {
  items: ContactSubmissionRow[]
  total: number
  page: number
  size: number
}


export interface AiCostWindow {
  cost_usd: number
  calls: number
  tokens: number
}

export interface AiBudgetInfo {
  monthly_usd: number | null
  month_to_date_usd: number
  pct_used: number | null
}

export interface AiCostsSummary {
  today: AiCostWindow
  last_7_days: AiCostWindow
  last_30_days: AiCostWindow
  all_time: AiCostWindow
  budget: AiBudgetInfo
}

export interface AiCostsDailyPoint {
  date: string
  cost_usd: number
  calls: number
}

export interface AiCostsBreakdownItem {
  key: string
  cost_usd: number
  calls: number
  tokens: number
}

export interface AiCostsUserItem {
  user_id: string | null
  email: string | null
  cost_usd: number
  calls: number
}

export interface AiCostsBreakdown {
  by_purpose: AiCostsBreakdownItem[]
  by_model: AiCostsBreakdownItem[]
  top_users: AiCostsUserItem[]
}

export interface AdminTableStat {
  table_name: string
  approx_row_count: number
  total_bytes: number
  rows_7d: number | null
  rows_30d: number | null
}

export interface AdminDatabaseStatsResponse {
  database_size_bytes: number
  tables: AdminTableStat[]
  generated_at: string
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

  getUserProfile(userId: string): Promise<AdminUserProfile> {
    return client.get(`/api/v1/admin/users/${userId}/profile`).then((r) => r.data)
  },

  getUserActivity(userId: string, page = 1, size = 25): Promise<AdminUserActivityResponse> {
    return client
      .get(`/api/v1/admin/users/${userId}/activity`, { params: { page, size } })
      .then((r) => r.data)
  },

  deleteUser(userId: string): Promise<void> {
    return client.delete(`/api/v1/admin/users/${userId}`).then(() => undefined)
  },

  sendPasswordReset(userId: string): Promise<void> {
    return client.post(`/api/v1/admin/users/${userId}/password-reset`).then(() => undefined)
  },

  verifyUser(userId: string): Promise<AdminUserRow> {
    return client.patch(`/api/v1/admin/users/${userId}/verify`).then((r) => r.data)
  },

  updateLimits(userId: string, dailyTailorLimitOverride: number | null): Promise<AdminUserProfile> {
    return client
      .patch(`/api/v1/admin/users/${userId}/limits`, {
        daily_tailor_limit_override: dailyTailorLimitOverride,
      })
      .then((r) => r.data)
  },

  listAiJobs(params: {
    kind?: string
    status?: string
    search?: string
    page?: number
    size?: number
  }): Promise<AdminAiJobListResponse> {
    return client.get('/api/v1/admin/ai-jobs', { params }).then((r) => r.data)
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

  listPipelineRuns(params: {
    pipeline_name?: string
    status?: string
    page?: number
    size?: number
  }): Promise<PipelineRunLogListResponse> {
    return client.get('/api/v1/admin/pipeline/runs', { params }).then((r) => r.data)
  },

  listRawJobs(params: {
    search?: string
    source?: string
    duplicate?: boolean
    remote?: boolean
    page?: number
    size?: number
  }): Promise<RawJobAdminListResponse> {
    return client.get('/api/v1/admin/raw-jobs', { params }).then((r) => r.data)
  },

  getSystemHealth(): Promise<SystemHealthResponse> {
    return client.get('/api/v1/admin/system/health').then((r) => r.data)
  },

  listAuditLogs(params: {
    action?: string
    user_id?: string
    page?: number
    size?: number
  }): Promise<AdminAuditLogListResponse> {
    return client.get('/api/v1/admin/audit-logs', { params }).then((r) => r.data)
  },

  sendBulkNotification(data: {
    audience: 'all' | 'role' | 'user'
    role?: string
    user_id?: string
    title: string
    body: string
    type?: string
  }): Promise<{ sent_count: number }> {
    return client.post('/api/v1/admin/notifications/bulk', data).then((r) => r.data)
  },

  listAdminNotifications(params: {
    search?: string
    page?: number
    size?: number
  }): Promise<AdminNotificationListResponse> {
    return client.get('/api/v1/admin/notifications/admin-messages', { params }).then((r) => r.data)
  },

  listBillingUsers(params: {
    search?: string
    status?: string
    page?: number
    size?: number
  }): Promise<AdminBillingUserListResponse> {
    return client.get('/api/v1/admin/billing/users', { params }).then((r) => r.data)
  },

  listContactSubmissions(params: {
    search?: string
    status?: string
    category?: string
    page?: number
    size?: number
  }): Promise<ContactSubmissionListResponse> {
    return client.get('/api/v1/admin/contact-submissions', { params }).then((r) => r.data)
  },

  updateContactSubmissionStatus(id: string, status: string): Promise<ContactSubmissionRow> {
    return client.patch(`/api/v1/admin/contact-submissions/${id}/status`, { status }).then((r) => r.data)
  },

  getAiCostsSummary(): Promise<AiCostsSummary> {
    return client.get('/api/v1/admin/ai-costs/summary').then((r) => r.data)
  },

  getAiCostsDaily(days = 30): Promise<AiCostsDailyPoint[]> {
    return client.get('/api/v1/admin/ai-costs/daily', { params: { days } }).then((r) => r.data)
  },

  getAiCostsBreakdown(days = 30): Promise<AiCostsBreakdown> {
    return client.get('/api/v1/admin/ai-costs/breakdown', { params: { days } }).then((r) => r.data)
  },

  updateAiBudget(monthlyUsd: number | null): Promise<AiCostsSummary> {
    return client.put('/api/v1/admin/ai-costs/budget', { monthly_usd: monthlyUsd }).then((r) => r.data)
  },

  getDatabaseStats(): Promise<AdminDatabaseStatsResponse> {
    return client.get('/api/v1/admin/database/stats').then((r) => r.data)
  },
}
