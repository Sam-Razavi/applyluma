import client from '../api/client'

export interface GmailConfirmation {
  code: string | null
  link: string | null
  received_at: string | null
}

export interface EmailForwardingStatus {
  enabled: boolean
  address: string | null
  emails_received: number
  last_received_at: string | null
  /** Gmail emails its "confirm forwarding" code to the address; shown here. */
  gmail_confirmation: GmailConfirmation | null
}

export function getEmailForwarding(): Promise<EmailForwardingStatus> {
  return client.get<EmailForwardingStatus>('/api/v1/email-forwarding').then((r) => r.data)
}

export function rotateEmailForwarding(): Promise<EmailForwardingStatus> {
  return client.post<EmailForwardingStatus>('/api/v1/email-forwarding/rotate').then((r) => r.data)
}

/** One email the user forwarded, and what ApplyLuma made of it. */
export interface ForwardedEmail {
  id: string
  from_address: string
  subject: string | null
  snippet: string | null
  received_at: string | null
  created_at: string
  classification: 'rejection' | 'interview' | 'offer' | 'acknowledged' | null
  suggested_status: string | null
  evidence: string | null
  suggestion_state: 'none' | 'pending' | 'accepted' | 'dismissed'
  application_id: string | null
  company_name: string | null
  job_title: string | null
  /** For an unmatched email: a guess at what it is about, to prefill the form. */
  guessed_company?: string | null
  guessed_title?: string | null
}

export function listForwardedEmails(params: {
  skip?: number
  limit?: number
  matched?: boolean
}): Promise<{ items: ForwardedEmail[]; total: number }> {
  return client
    .get<{ items: ForwardedEmail[]; total: number }>('/api/v1/email-forwarding/messages', { params })
    .then((r) => r.data)
}

export function deleteForwardedEmail(emailId: string): Promise<void> {
  return client.delete(`/api/v1/email-forwarding/messages/${emailId}`).then(() => undefined)
}

/** Start tracking the application an email is about; ties the email to it. */
export function createApplicationFromEmail(
  emailId: string,
  body: { company_name: string; job_title: string },
): Promise<{ id: string; company_name: string; job_title: string; status: string }> {
  return client
    .post(`/api/v1/email-forwarding/messages/${emailId}/application`, body)
    .then((r) => r.data)
}
