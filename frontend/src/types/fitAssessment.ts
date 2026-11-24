export type FitRecommendation = 'high_priority' | 'consider' | 'low_priority'
export type FitImportance = 'mandatory' | 'preferred' | 'unclear'
export type FitStatus = 'met' | 'partly_met' | 'not_met' | 'not_enough_information'

export interface FitRequirement {
  id: string
  text: string
  category: string
  importance: FitImportance
  ad_quote: string
  ad_quote_found: boolean
  status: FitStatus
  cv_quote: string
  /** null when the model gave no quote. */
  cv_quote_found: boolean | null
  /** The model's judgement was set aside: its CV quote was missing or not in the CV. */
  downgraded: boolean
  /** What the model said before the quote check (from prompt 5 on). */
  model_status?: FitStatus
  /** Why it was set aside (from rules 2 on): "cv_quote_missing" or "cv_quote_not_found". */
  downgrade_reason?: string
  note: string
}

export interface FitResult {
  recommendation: FitRecommendation
  rule: string
  reason: string
  limited_information: boolean
  /** Mandatory requirements whose wording was not found in the ad (rules 2 on). */
  mandatory_unverified?: number
  summary: string
  missing_information: string[]
  requirements: FitRequirement[]
}

export interface FitAssessment {
  id: string
  raw_job_posting_id: string | null
  job_title: string
  company: string
  status: 'pending' | 'processing' | 'complete' | 'failed'
  error_message: string | null
  recommendation: FitRecommendation | null
  limited_information: boolean | null
  result: FitResult | null
  model: string
  prompt_version: string
  rules_version: string
  created_at: string
}

export interface FitAssessmentStatus {
  enabled: boolean
  daily_limit: number | null
  used_today: number
}
