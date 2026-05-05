import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        token: null,
        setToken: (token) => set({ token }),
        logout: () => set({ token: null }),
      }),
      { name: 'auth' },
    ),
    { name: 'AuthStore' },
  ),
)
