import client from '../api/client'

interface CheckoutSessionResponse {
  checkout_url: string
}

interface PortalSessionResponse {
  portal_url: string
}

interface BillingStatusResponse {
  configured: boolean
  test_mode: boolean
}

export function createCheckoutSession(): Promise<CheckoutSessionResponse> {
  return client
    .post<CheckoutSessionResponse>('/api/v1/billing/create-checkout-session')
    .then((r) => r.data)
}

export function createPortalSession(): Promise<PortalSessionResponse> {
  return client.get<PortalSessionResponse>('/api/v1/billing/portal').then((r) => r.data)
}

export function getBillingStatus(): Promise<BillingStatusResponse> {
  return client.get<BillingStatusResponse>('/api/v1/billing/status').then((r) => r.data)
}
