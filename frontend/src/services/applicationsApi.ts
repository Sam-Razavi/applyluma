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

export function fetchApplications(statusFilter?: ApplicationStatus): Promise<Application[]> {
  return client
    .get<Application[]>('/api/v1/applications', {
      params: statusFilter ? { status: statusFilter } : undefined,
    })
    .then((r) => r.data.map(normalizeApplication))
}

export function createApplication(data: ApplicationCreate): Promise<Application> {
  return client.post<Application>('/api/v1/applications', data).then((r) => normalizeApplication(r.data))
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
