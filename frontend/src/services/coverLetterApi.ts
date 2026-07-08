import client from '../api/client'
import type {
  CoverLetterJob,
  CoverLetterPreview,
  CoverLetterStatusResponse,
  CoverLetterTone,
  CoverLetterUsage,
} from '../types/coverLetter'

export const coverLetterApi = {
  getUsage: (): Promise<CoverLetterUsage> =>
    client.get<CoverLetterUsage>('/api/v1/cover-letters/usage').then((r) => r.data),

  submit: (
    cvId: string,
    jobDescriptionId: string | null,
    tone: CoverLetterTone,
    rawJobPostingId?: string,
  ): Promise<CoverLetterJob> =>
    client
      .post<CoverLetterJob>('/api/v1/cover-letters/generate', {
        cv_id: cvId,
        ...(rawJobPostingId
          ? { raw_job_posting_id: rawJobPostingId }
          : { job_description_id: jobDescriptionId }),
        tone,
      })
      .then((r) => r.data),

  getStatus: (jobId: string): Promise<CoverLetterStatusResponse> =>
    client
      .get<CoverLetterStatusResponse>(`/api/v1/cover-letters/${jobId}/status`)
      .then((r) => r.data),

  getPreview: (jobId: string): Promise<CoverLetterPreview> =>
    client.get<CoverLetterPreview>(`/api/v1/cover-letters/${jobId}`).then((r) => r.data),

  save: (jobId: string, savedText: string, title?: string): Promise<CoverLetterJob> =>
    client
      .post<CoverLetterJob>(`/api/v1/cover-letters/${jobId}/save`, {
        saved_text: savedText,
        title: title ?? null,
      })
      .then((r) => r.data),

  download: async (jobId: string, filename: string, templateId?: string): Promise<void> => {
    const response = await client.get(`/api/v1/cover-letters/${jobId}/download`, {
      responseType: 'blob',
      params: templateId ? { template: templateId } : undefined,
    })
    const url = URL.createObjectURL(new Blob([response.data as BlobPart], { type: 'application/pdf' }))
    const stem = filename.replace(/\.[^.]+$/, '').trim()
    const a = document.createElement('a')
    a.href = url
    a.download = `${stem || 'cover-letter'}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },

  list: (): Promise<CoverLetterJob[]> =>
    client.get<CoverLetterJob[]>('/api/v1/cover-letters/history').then((r) => r.data),

  remove: (jobId: string): Promise<void> =>
    client.delete(`/api/v1/cover-letters/${jobId}`).then(() => undefined),
}
