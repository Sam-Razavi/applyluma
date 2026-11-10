import client from '../api/client'
import type {
  Application,
  ApplicationAnalytics,
  ApplicationContact,
  ApplicationContactCreate,
  ApplicationCreate,
  ApplicationStats,
  ApplicationStatus,
  ApplicationUpdate,
} from '../types/application'

function normalizeApplication(application: Application): Application {
  return {
    ...application,
    events: application.events ?? [],
    contacts: application.contacts ?? [],
  }
}

// The list endpoint caps each page (default 100, max 500). The board filters
// and searches client-side, so it needs every application, not just the
// first page — fetch pages until a short one comes back.
const APPLICATIONS_PAGE_SIZE = 500

export async function fetchApplications(statusFilter?: ApplicationStatus): Promise<Application[]> {
  const all: Application[] = []
  for (let skip = 0; ; skip += APPLICATIONS_PAGE_SIZE) {
    const { data } = await client.get<Application[]>('/api/v1/applications', {
      params: {
        ...(statusFilter ? { status: statusFilter } : {}),
        skip,
        limit: APPLICATIONS_PAGE_SIZE,
      },
    })
    all.push(...data.map(normalizeApplication))
    if (data.length < APPLICATIONS_PAGE_SIZE) return all
  }
}

export function createApplication(data: ApplicationCreate): Promise<Application> {
  return client.post<Application>('/api/v1/applications', data).then((r) => normalizeApplication(r.data))
}

export interface DuplicateCheckResponse {
  duplicate: boolean
  /** "url": this exact posting is already tracked; "company": another open application there. */
  match: 'url' | 'company' | null
  application: {
    id: string
    company_name: string
    job_title: string
    status: string
    created_at: string
  } | null
}

export function checkDuplicateApplication(query: {
  company?: string | null
  jobUrl?: string | null
}): Promise<DuplicateCheckResponse> {
  const params: Record<string, string> = {}
  if (query.company) params.company = query.company
  if (query.jobUrl) params.job_url = query.jobUrl
  return client
    .get<DuplicateCheckResponse>('/api/v1/applications/check-duplicate', { params })
    .then((r) => r.data)
}

export function updateApplication(id: string, data: ApplicationUpdate): Promise<Application> {
  return client
    .patch<Application>(`/api/v1/applications/${id}`, data)
    .then((r) => normalizeApplication(r.data))
}

export function deleteApplication(id: string): Promise<void> {
  return client.delete(`/api/v1/applications/${id}`).then(() => undefined)
}

export function fetchStats(): Promise<ApplicationStats> {
  return client.get<ApplicationStats>('/api/v1/applications/stats').then((r) => r.data)
}

export function fetchApplicationAnalytics(): Promise<ApplicationAnalytics> {
  return client
    .get<ApplicationAnalytics>('/api/v1/applications/analytics')
    .then((r) => r.data)
}

export function addApplicationContact(
  applicationId: string,
  data: ApplicationContactCreate,
): Promise<ApplicationContact> {
  return client
    .post<ApplicationContact>(`/api/v1/applications/${applicationId}/contacts`, data)
    .then((r) => r.data)
}

export function deleteApplicationContact(
  applicationId: string,
  contactId: string,
): Promise<void> {
  return client
    .delete(`/api/v1/applications/${applicationId}/contacts/${contactId}`)
    .then(() => undefined)
}

export interface EmailSuggestion {
  id: string
  application_id: string
  company_name: string
  job_title: string
  current_status: ApplicationStatus
  suggested_status: ApplicationStatus
  classification: string
  confidence: number
  /** The sentence the classification was based on. */
  evidence: string | null
  from_address: string
  subject: string | null
  received_at: string | null
}

export function listEmailSuggestions(): Promise<{ items: EmailSuggestion[] }> {
  return client
    .get<{ items: EmailSuggestion[] }>('/api/v1/applications/email-suggestions')
    .then((r) => r.data)
}

export function acceptEmailSuggestion(suggestionId: string): Promise<Application> {
  return client
    .post<Application>(`/api/v1/applications/email-suggestions/${suggestionId}/accept`)
    .then((r) => r.data)
}

export function dismissEmailSuggestion(suggestionId: string): Promise<void> {
  return client
    .post(`/api/v1/applications/email-suggestions/${suggestionId}/dismiss`)
    .then(() => undefined)
}

/** A forwarded email that clearly says something but matched no application. */
export interface UnmatchedEmail {
  id: string
  from_address: string
  subject: string | null
  classification: string
  suggested_status: ApplicationStatus
  evidence: string | null
  received_at: string | null
  created_at: string
}

export function listUnmatchedEmails(): Promise<{ items: UnmatchedEmail[] }> {
  return client
    .get<{ items: UnmatchedEmail[] }>('/api/v1/applications/email-unmatched')
    .then((r) => r.data)
}

export function assignUnmatchedEmail(emailId: string, applicationId: string): Promise<Application> {
  return client
    .post<Application>(`/api/v1/applications/email-unmatched/${emailId}/assign`, {
      application_id: applicationId,
    })
    .then((r) => r.data)
}

export function dismissUnmatchedEmail(emailId: string): Promise<void> {
  return client
    .post(`/api/v1/applications/email-unmatched/${emailId}/dismiss`)
    .then(() => undefined)
}
