import { create } from 'zustand'
import { createJSONStorage, devtools, persist } from 'zustand/middleware'
import type { User } from '../types'
import posthog from 'posthog-js'

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
          posthog.identify(user.id, { email: user.email, role: user.role })
          set({ token, refreshToken, user, isAuthenticated: true })
        },
        logout: () => {
          posthog.reset()
          set({ token: null, refreshToken: null, user: null, isAuthenticated: false })
        },
        setUser: (user) => {
          posthog.identify(user.id, { email: user.email, role: user.role })
          set({ user, isAuthenticated: true })
        },
        setLoading: (isLoading) => set({ isLoading }),
      }),
      {
        name: 'auth',
        // sessionStorage keeps tokens scoped to a single browser session rather
        // than persisting them indefinitely in localStorage (reduces XSS blast
        // radius). Full httpOnly-cookie auth is the long-term goal.
        storage: createJSONStorage(() => sessionStorage),
        partialize: (state) => ({ token: state.token, refreshToken: state.refreshToken, user: state.user }),
      },
    ),
    { name: 'AuthStore' },
  ),
)
