import client from '../api/client'
import type { KeywordsByType } from '../types/jobDiscovery'

export interface AdzunaJobResult {
  id: string
  title: string
  company_name: string
  location: string
  salary_min: number | null
  salary_max: number | null
  contract_type: string | null
  redirect_url: string
  description: string
  created: string | null
  source?: string
}

export interface JobSearchResponse {
  results: AdzunaJobResult[]
  count: number
  page: number
  total_pages: number
}

export interface AnalyzeTextResponse {
  keywords: KeywordsByType
  matched_skills: string[]
  missing_skills: string[]
}

export interface BookmarkResponse {
  id: string
  source_raw_job_posting_id: string | null
}

export function searchJobs(
  q: string,
  location?: string,
  page = 1,
  resultsPerPage = 10,
  source: 'all' | 'adzuna' | 'platsbanken' = 'all',
): Promise<JobSearchResponse> {
  return client
    .get<JobSearchResponse>('/api/v1/jobs/search', {
      params: {
        q,
        location: location || undefined,
        page,
        results_per_page: resultsPerPage,
        source,
      },
    })
    .then((r) => r.data)
}

export function analyzeJobText(description: string): Promise<AnalyzeTextResponse> {
  return client
    .post<AnalyzeTextResponse>('/api/v1/jobs/analyze-text', { description })
    .then((r) => r.data)
}

export function bookmarkSearchJob(job: AdzunaJobResult): Promise<BookmarkResponse> {
  return client
    .post<BookmarkResponse>('/api/v1/jobs/bookmark', {
      title: job.title,
      company: job.company_name,
      url: job.redirect_url,
      description: job.description,
      source: job.source ?? 'adzuna',
      location: job.location || null,
      salary_min: job.salary_min,
      salary_max: job.salary_max,
      contract_type: job.contract_type,
    })
    .then((r) => r.data)
}
