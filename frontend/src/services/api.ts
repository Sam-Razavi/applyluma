import client from '../api/client'
import type { TokenPair, User } from '../types'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export const authApi = {
  login: (data: LoginRequest): Promise<TokenPair> =>
    client.post<TokenPair>('/api/v1/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest): Promise<User> =>
    client.post<User>('/api/v1/auth/register', data).then((r) => r.data),

  me: (): Promise<User> =>
    client.get<User>('/api/v1/auth/me').then((r) => r.data),
}
