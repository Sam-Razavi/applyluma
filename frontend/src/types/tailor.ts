export type TailorIntensity = 'light' | 'medium' | 'aggressive'
export type TailorStatus = 'pending' | 'processing' | 'complete' | 'failed'

export interface TailorJob {
  id: string
  cv_id: string
  job_description_id: string
  intensity: TailorIntensity
  status: TailorStatus
  language: string | null
  output_cv_id: string | null
  created_at: string
}

export interface TailorStatusResponse {
  id: string
  status: TailorStatus
  error_message: string | null
  language: string | null
  output_cv_id: string | null
}

export interface TailorSection {
  section_id: string
  section_name: string
  original: string
  tailored: string
  changes: string[]
}

export interface TailorMeta {
  keywords_added: string[]
  keywords_already_present: string[]
  intensity_applied: string
}

export interface TailorPreview {
  job_id: string
  language: string
  sections: TailorSection[]
  meta: TailorMeta
}

export interface TailorUsage {
  used_today: number
  daily_limit: number | null
  resets_at: string
}
