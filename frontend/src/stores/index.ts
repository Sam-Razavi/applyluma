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
        // Persist only non-sensitive session state. Raw tokens are no longer
        // stored in JS-accessible storage — the server sets httpOnly cookies on
        // login so tokens are invisible to XSS. isAuthenticated + user let the
        // UI know the session is live without exposing credentials.
        storage: createJSONStorage(() => sessionStorage),
        partialize: (state) => ({ isAuthenticated: state.isAuthenticated, user: state.user }),
      },
    ),
    // Redux DevTools can inspect this store's live memory state, which
    // includes the in-memory token/refreshToken — only wire it up in dev.
    { name: 'AuthStore', enabled: import.meta.env.DEV },
  ),
)
