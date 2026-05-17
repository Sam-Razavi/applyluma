import client from '../api/client'

export const authApi = {
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
