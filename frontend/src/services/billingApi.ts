import client from '../api/client'

interface CheckoutSessionResponse {
  checkout_url: string
}

interface PortalSessionResponse {
  portal_url: string
}

export function createCheckoutSession(): Promise<CheckoutSessionResponse> {
  return client
    .post<CheckoutSessionResponse>('/api/v1/billing/create-checkout-session')
    .then((r) => r.data)
}

export function createPortalSession(): Promise<PortalSessionResponse> {
  return client.get<PortalSessionResponse>('/api/v1/billing/portal').then((r) => r.data)
}
