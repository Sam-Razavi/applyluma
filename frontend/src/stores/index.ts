import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { User } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setToken: (token: string) => void
  login: (token: string, user: User) => void
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
        isAuthenticated: false,
        isLoading: false,
        setToken: (token) => {
          console.log('[AuthStore] setToken called, token present:', !!token)
          set({ token })
        },
        login: (token, user) => {
          console.log('[AuthStore] login called, token present:', !!token, 'user:', user.email)
          set({ token, user, isAuthenticated: true })
        },
        logout: () => set({ token: null, user: null, isAuthenticated: false }),
        setUser: (user) => set({ user, isAuthenticated: true }),
        setLoading: (isLoading) => set({ isLoading }),
      }),
      {
        name: 'auth',
        partialize: (state) => ({ token: state.token, user: state.user }),
      },
    ),
    { name: 'AuthStore' },
  ),
)
