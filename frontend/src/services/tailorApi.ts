import client from '../api/client'
import type {
  TailorIntensity,
  TailorJob,
  TailorPreview,
  TailorStatusResponse,
  TailorUsage,
} from '../types/tailor'

export const tailorApi = {
  getUsage: (): Promise<TailorUsage> =>
    client.get<TailorUsage>('/api/v1/tailor/usage').then((r) => r.data),

  submit: (
    cvId: string,
    jobDescriptionId: string,
    intensity: TailorIntensity,
  ): Promise<TailorJob> =>
    client
      .post<TailorJob>('/api/v1/tailor/submit', {
        cv_id: cvId,
        job_description_id: jobDescriptionId,
        intensity,
      })
      .then((r) => r.data),

  getStatus: (jobId: string): Promise<TailorStatusResponse> =>
    client.get<TailorStatusResponse>(`/api/v1/tailor/${jobId}/status`).then((r) => r.data),

  getPreview: (jobId: string): Promise<TailorPreview> =>
    client.get<TailorPreview>(`/api/v1/tailor/${jobId}/preview`).then((r) => r.data),

  save: (
    jobId: string,
    acceptedSectionIds: string[] | null,
    cvTitle?: string,
  ): Promise<{ cv_id: string; title: string; file_url: string | null }> =>
    client
      .post(`/api/v1/tailor/${jobId}/save`, {
        accepted_section_ids: acceptedSectionIds,
        cv_title: cvTitle,
      })
      .then((r) => r.data),

  getHistory: (): Promise<TailorJob[]> =>
    client.get<TailorJob[]>('/api/v1/tailor/history').then((r) => r.data),
}
