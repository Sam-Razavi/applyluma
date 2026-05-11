export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  role: 'user' | 'admin' | 'premium'
  created_at: string
  updated_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
}

export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface CV {
  id: string
  user_id: string
  title: string
  filename: string
  content: string | null
  file_url: string | null
  file_size: number | null
  is_default: boolean
  is_tailored: boolean
  parent_cv_id: string | null
  tailor_job_id: string | null
  created_at: string
  updated_at: string
}

export interface JobDescription {
  id: string
  user_id: string
  company_name: string
  job_title: string
  description: string
  url: string | null
  keywords: string[]
  created_at: string
  updated_at: string
}

export interface AIAnalysis {
  match_score: number
  strengths: string[]
  gaps: string[]
  recommendations: string[]
  full_analysis: string
}

export type TrendDirection = 'up' | 'down' | 'stable'
export type Granularity = 'daily' | 'weekly' | 'monthly'
export type ExperienceLevel = 'junior' | 'mid' | 'senior' | 'management'

export interface ResponseMetadata {
  timestamp: string
  data_freshness_hours: number
  sample_size: number
  applied_filters: Record<string, unknown>
  next_update: string | null
}

export interface ErrorDetail {
  code: string
  message: string
  details?: Record<string, unknown> | null
}

export interface AnalyticsEnvelope<T> {
  success: boolean
  data: T | null
  metadata: ResponseMetadata | null
  error: ErrorDetail | null
}

export interface SkillTrend {
  skill: string
  frequency: number
  frequency_pct: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  trending_score_pct: number
  trend: TrendDirection
}

export interface SalaryInsightItem {
  dimension_type: string
  dimension_value: string
  p25_salary: number | null
  p50_salary: number | null
  p75_salary: number | null
  p90_salary: number | null
  avg_salary: number | null
  min_salary_floor: number | null
  max_salary_ceiling: number | null
  job_count: number
}

export interface HiringPatternPoint {
  period: string
  job_count: number
  remote_count: number
  remote_percentage: number
  avg_salary: number | null
}

export interface CompanyInsight {
  company_name: string
  total_jobs: number
  remote_jobs: number
  remote_percentage: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  most_common_employment_type: string | null
  first_seen_date: string
  last_seen_date: string
  hiring_velocity: number
}

export interface JobMarketHealth {
  total_jobs: number
  unique_companies: number
  remote_percentage: number
  avg_salary_midpoint: number | null
  senior_role_pct: number
  junior_role_pct: number
  management_role_pct: number
  mid_role_pct: number
  avg_skills_per_job: number
  data_date_range_days: number
  last_updated: string | null
}

export interface SkillDemand {
  skill: string
  total_mentions: number
  mentions_this_week: number
  mentions_last_week: number
  trending_score_pct: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  trend: TrendDirection
}

export interface LocationTrend {
  location: string
  job_count: number
  pct_of_total: number
  avg_salary_midpoint: number | null
  remote_percentage: number | null
}

export interface IndustryBreakdown {
  industry: string
  job_count: number
  pct_of_total: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  remote_percentage: number
}

export interface ExperienceLevelBreakdown {
  level: ExperienceLevel
  job_count: number
  pct_of_total: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  remote_percentage: number
}

export interface JobTypeMixItem {
  job_type: string
  remote_label: string
  job_count: number
  pct_of_total: number
  avg_salary_min: number | null
  avg_salary_max: number | null
}

export interface SalaryBySkill {
  skill: string
  avg_salary: number | null
  p25_salary: number | null
  p50_salary: number | null
  p75_salary: number | null
  p90_salary: number | null
  min_salary_floor: number | null
  max_salary_ceiling: number | null
  job_count: number
}

export interface SkillGap {
  skill: string
  in_resume: boolean
  market_demand_rank: number
  total_market_mentions: number
  trending_score_pct: number
  avg_salary_min: number | null
  avg_salary_max: number | null
  trend: TrendDirection
}

export interface ResumeComparison {
  resume_id: string
  resume_title: string
  resume_skill_count: number
  matched_skills: string[]
  missing_high_demand_skills: string[]
  skill_details: SkillGap[]
  market_salary_benchmark: SalaryInsightItem | null
  skills_market_coverage_pct: number
  overall_market_alignment_score: number
}
