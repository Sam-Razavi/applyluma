export interface DiscoveredJob {
  job_id: string
  title: string
  company: string
  location: string | null
  salary_min: number | null
  salary_max: number | null
  employment_type: string | null
  remote_allowed: boolean
  url: string
  source: string
  scraped_at: string
  match_score: number | null
  skills_match: number | null
  experience_match: number | null
  salary_match_score: number | null
  education_match: number | null
  location_match: number | null
  explanation: string | null
  keywords: ExtractedKeyword[]
  is_saved: boolean
  saved_job_id?: string | null
  application_status?: string | null
  application_id?: string | null
}

export interface DiscoveredJobDetail extends DiscoveredJob {
  description: string
  matched_skills: string[]
  missing_skills: string[]
}

export interface ExtractedKeyword {
  id: string
  raw_job_posting_id: string
  keyword: string
  keyword_type: string
  confidence_score: number
  frequency: number
  created_at: string
}

export interface KeywordsByType {
  technical_skills: string[]
  frameworks: string[]
  tools: string[]
  soft_skills: string[]
  languages: string[]
  certifications: string[]
}

export interface SavedJob {
  id: string
  user_id: string
  raw_job_posting_id: string
  list_name: string | null
  notes: string | null
  starred: boolean
  created_at: string
  updated_at: string
  job: DiscoveredJob | null
}

export interface JobFilters {
  location: string
  salary_min: string
  salary_max: string
  keywords: string
  source: string
  match_score_min: string
  sort: string
}

export const JOB_SOURCES = ['platsbanken', 'jobbsafari', 'indeed_se'] as const
export type JobSource = (typeof JOB_SOURCES)[number]

export const SOURCE_LABELS: Record<string, string> = {
  platsbanken: 'Platsbanken',
  jobbsafari: 'Jobbsafari',
  indeed_se: 'Indeed.se',
}
