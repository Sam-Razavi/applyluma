export type CoverLetterTone = 'formal' | 'friendly' | 'concise'
export type CoverLetterStatus = 'pending' | 'processing' | 'complete' | 'failed'

export interface CoverLetterJob {
  id: string
  cv_id: string
  job_description_id: string
  tone: CoverLetterTone
  status: CoverLetterStatus
  language: string | null
  word_count: number | null
  title: string | null
  is_saved: boolean
  created_at: string
}

export interface CoverLetterStatusResponse {
  id: string
  status: CoverLetterStatus
  error_message: string | null
}

export interface CoverLetterPreview {
  id: string
  generated_text: string
  language: string
  word_count: number | null
  tone: CoverLetterTone
}

export interface CoverLetterUsage {
  used_today: number
  daily_limit: number | null
  resets_at: string
}
