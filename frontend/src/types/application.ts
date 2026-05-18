export type ApplicationStatus =
  | 'wishlist'
  | 'applied'
  | 'phone_screen'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn'

export interface ApplicationEvent {
  id: string
  application_id: string
  event_type: string
  old_value: string | null
  new_value: string | null
  description: string | null
  event_date: string
  created_at: string
}

export interface ApplicationContact {
  id: string
  application_id: string
  name: string | null
  role: string | null
  email: string | null
  phone: string | null
  linkedin_url: string | null
  notes: string | null
  created_at: string
}

export interface Application {
  id: string
  user_id: string
  job_description_id: string | null
  raw_job_posting_id: string | null
  cv_id: string | null
  company_name: string
  job_title: string
  job_url: string | null
  status: ApplicationStatus
  applied_date: string | null
  source: string | null
  salary_min: number | null
  salary_max: number | null
  location: string | null
  remote_type: string | null
  priority: number
  notes: string | null
  events: ApplicationEvent[]
  contacts: ApplicationContact[]
  created_at: string
  updated_at: string
}

export interface ApplicationCreate {
  company_name?: string | null
  job_title?: string | null
  job_description_id?: string | null
  raw_job_posting_id?: string | null
  cv_id?: string | null
  job_url?: string | null
  status?: ApplicationStatus
  applied_date?: string | null
  source?: string | null
  salary_min?: number | null
  salary_max?: number | null
  location?: string | null
  remote_type?: string | null
  priority?: number
  notes?: string | null
}

export type ApplicationUpdate = Partial<ApplicationCreate>

export type ApplicationStats = Record<ApplicationStatus, number>

export interface ApplicationFunnelCount {
  status: ApplicationStatus
  count: number
}

export interface WeeklyApplicationCount {
  week_start: string
  count: number
}

export interface ApplicationSourceCount {
  source: string
  count: number
}

export interface ApplicationSalaryBucketCount {
  bucket: string
  count: number
}

export interface ApplicationAnalytics {
  funnel: ApplicationFunnelCount[]
  response_rate: number
  offer_rate: number
  average_response_days: number | null
  weekly_counts: WeeklyApplicationCount[]
  top_sources: ApplicationSourceCount[]
  salary_distribution: ApplicationSalaryBucketCount[]
}

export interface ApplicationContactCreate {
  name?: string | null
  role?: string | null
  email?: string | null
  phone?: string | null
  linkedin_url?: string | null
  notes?: string | null
}

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  'wishlist',
  'applied',
  'phone_screen',
  'interview',
  'offer',
  'rejected',
  'withdrawn',
]
