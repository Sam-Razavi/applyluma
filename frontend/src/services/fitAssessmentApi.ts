import client from '../api/client'
import type { FitAssessment, FitAssessmentStatus } from '../types/fitAssessment'

const BASE = '/api/v1/fit-assessments'

export const fitAssessmentApi = {
  status: (): Promise<FitAssessmentStatus> =>
    client.get<FitAssessmentStatus>(`${BASE}/status`).then((r) => r.data),

  latest: (rawJobPostingId: string): Promise<FitAssessment | null> =>
    client
      .get<FitAssessment | null>(`${BASE}/latest`, { params: { raw_job_posting_id: rawJobPostingId } })
      .then((r) => r.data),

  request: (rawJobPostingId: string, force = false): Promise<FitAssessment> =>
    client
      .post<FitAssessment>(BASE, { raw_job_posting_id: rawJobPostingId, force })
      .then((r) => r.data),

  get: (id: string): Promise<FitAssessment> =>
    client.get<FitAssessment>(`${BASE}/${id}`).then((r) => r.data),
}
