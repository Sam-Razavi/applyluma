import client from '../api/client'
import type { User } from '../types'

export const authApi = {
  verifyEmail: (token: string): Promise<User> =>
    client.get<User>(`/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`).then((r) => r.data),

  resendVerification: (): Promise<void> =>
    client.post('/api/v1/auth/resend-verification').then(() => undefined),

  updateProfile: (fullName: string): Promise<User> =>
    client.patch<User>('/api/v1/auth/me', { full_name: fullName }).then((r) => r.data),

  changePassword: (currentPassword: string, newPassword: string): Promise<void> =>
    client
      .post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      .then(() => undefined),

  deleteAccount: (): Promise<void> =>
    client.delete('/api/v1/auth/me').then(() => undefined),
}
