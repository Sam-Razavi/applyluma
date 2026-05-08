export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
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
