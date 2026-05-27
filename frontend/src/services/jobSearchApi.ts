import client from '../api/client'

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
}

export interface JobSearchResponse {
  results: AdzunaJobResult[]
  count: number
  page: number
  total_pages: number
}

export function searchJobs(
  q: string,
  location?: string,
  page = 1,
  resultsPerPage = 10,
): Promise<JobSearchResponse> {
  return client
    .get<JobSearchResponse>('/api/v1/jobs/search', {
      params: {
        q,
        location: location || undefined,
        page,
        results_per_page: resultsPerPage,
      },
    })
    .then((r) => r.data)
}
