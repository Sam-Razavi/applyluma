import client from '../api/client'
import type { JobDescription } from '../types'
import type { DiscoveredJob, DiscoveredJobDetail, JobFilters, KeywordsByType, SavedJob } from '../types/jobDiscovery'

export interface JobsResponse {
  jobs: DiscoveredJob[]
  total: number
  page: number
  limit: number
}

export function fetchDiscoveredJobs(filters: Partial<JobFilters> & { page?: number; limit?: number }): Promise<DiscoveredJob[]> {
  return client
    .get<DiscoveredJob[]>('/api/v1/jobs', {
      params: {
        search: filters.search || undefined,
        location: filters.location || undefined,
        salary_min: filters.salary_min || undefined,
        salary_max: filters.salary_max || undefined,
        keywords: filters.keywords || undefined,
        source: filters.source || undefined,
        is_remote: filters.remote_only ? true : undefined,
        match_score_min: filters.match_score_min || undefined,
        sort: filters.sort || 'score_desc',
        page: filters.page ?? 1,
        limit: filters.limit ?? 20,
      },
    })
    .then((r) => r.data)
}

export function fetchJobDetail(jobId: string): Promise<DiscoveredJobDetail> {
  return client.get<DiscoveredJobDetail>(`/api/v1/jobs/${jobId}`).then((r) => r.data)
}

export function fetchJobKeywords(jobId: string): Promise<KeywordsByType> {
  return client.get<KeywordsByType>(`/api/v1/jobs/${jobId}/keywords`).then((r) => r.data)
}

export interface SaveJobPayload {
  job_id: string
  list_name?: string
  notes?: string
}

export function saveJob(payload: SaveJobPayload): Promise<JobDescription> {
  return client.post<JobDescription>('/api/v1/job-descriptions/from-discover', {
    raw_job_posting_id: payload.job_id,
    list_name: payload.list_name,
    notes: payload.notes,
  }).then((r) => r.data)
}

export function fetchSavedJobs(listName?: string): Promise<SavedJob[]> {
  return client
    .get<SavedJob[]>('/api/v1/saved-jobs', {
      params: listName ? { list_name: listName } : undefined,
    })
    .then((r) => r.data)
}

export interface UpdateSavedJobPayload {
  list_name?: string | null
  notes?: string | null
  starred?: boolean
}

export function updateSavedJob(savedJobId: string, payload: UpdateSavedJobPayload): Promise<SavedJob> {
  return client.patch<SavedJob>(`/api/v1/saved-jobs/${savedJobId}`, payload).then((r) => r.data)
}

export function deleteSavedJob(jdId: string): Promise<void> {
  return client.delete(`/api/v1/job-descriptions/${jdId}`).then(() => undefined)
}
