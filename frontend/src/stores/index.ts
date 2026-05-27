import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { User } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setToken: (token: string) => void
  login: (token: string, refreshToken: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
  setLoading: (isLoading: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        setToken: (token) => {
          set({ token })
        },
        login: (token, refreshToken, user) => {
          set({ token, refreshToken, user, isAuthenticated: true })
        },
        logout: () => set({ token: null, refreshToken: null, user: null, isAuthenticated: false }),
        setUser: (user) => set({ user, isAuthenticated: true }),
        setLoading: (isLoading) => set({ isLoading }),
      }),
      {
        name: 'auth',
        partialize: (state) => ({ token: state.token, refreshToken: state.refreshToken, user: state.user }),
      },
    ),
    { name: 'AuthStore' },
  ),
)
