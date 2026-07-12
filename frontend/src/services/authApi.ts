import client from '../api/client'
import type { TokenPair, User } from '../types'

export interface AuthProviders {
  google: boolean
  linkedin: boolean
  github: boolean
  magic_link: boolean
}

export const authApi = {
  getProviders: (): Promise<AuthProviders> =>
    client.get<AuthProviders>('/api/v1/auth/providers').then((r) => r.data),

  requestMagicLink: (email: string): Promise<void> =>
    client.post('/api/v1/auth/magic-link', { email }).then(() => undefined),

  verifyMagicLink: (token: string): Promise<TokenPair> =>
    client.post<TokenPair>('/api/v1/auth/magic-link/verify', { token }).then((r) => r.data),

  verifyEmail: (token: string): Promise<User> =>
    client.get<User>(`/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`).then((r) => r.data),

  resendVerification: (): Promise<void> =>
    client.post('/api/v1/auth/resend-verification').then(() => undefined),

  updateProfile: (data: { full_name?: string; preferred_template?: string }): Promise<User> =>
    client.patch<User>('/api/v1/auth/me', data).then((r) => r.data),

  changePassword: (currentPassword: string, newPassword: string): Promise<void> =>
    client
      .post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      .then(() => undefined),

  deleteAccount: (): Promise<void> =>
    client.delete('/api/v1/auth/me').then(() => undefined),

  logout: (refreshToken?: string): Promise<void> =>
    client
      .post('/api/v1/auth/logout', { refresh_token: refreshToken ?? null })
      .then(() => undefined),

  forgotPassword: (email: string): Promise<void> =>
    client.post('/api/v1/auth/forgot-password', { email }).then(() => undefined),

  resetPassword: (token: string, newPassword: string): Promise<void> =>
    client
      .post('/api/v1/auth/reset-password', { token, new_password: newPassword })
      .then(() => undefined),
}
