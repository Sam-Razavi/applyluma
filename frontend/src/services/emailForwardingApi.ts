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
