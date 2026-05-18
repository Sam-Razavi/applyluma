import client from '../api/client'
import type {
  TailorIntensity,
  TailorJob,
  TailorPreview,
  TailorStatusResponse,
  TailorUsage,
} from '../types/tailor'

export type TailorSubmitPayload =
  | {
      cv_id: string
      job_description_id: string
      raw_job_posting_id?: never
      intensity: TailorIntensity
    }
  | {
      cv_id: string
      raw_job_posting_id: string
      job_description_id?: never
      intensity: TailorIntensity
    }

export const tailorApi = {
  getUsage: (): Promise<TailorUsage> =>
    client.get<TailorUsage>('/api/v1/tailor/usage').then((r) => r.data),

  submit: (
    cvOrPayload: string | TailorSubmitPayload,
    jobDescriptionId?: string,
    intensity?: TailorIntensity,
  ): Promise<TailorJob> => {
    const payload =
      typeof cvOrPayload === 'string'
        ? {
            cv_id: cvOrPayload,
            job_description_id: jobDescriptionId,
            intensity,
          }
        : cvOrPayload

    return client.post<TailorJob>('/api/v1/tailor/submit', payload).then((r) => r.data)
  },

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

  download: async (jobId: string, filename: string): Promise<void> => {
    const response = await client.get(`/api/v1/tailor/${jobId}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([response.data as BlobPart], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },
}
