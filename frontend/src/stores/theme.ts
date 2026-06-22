import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
  dark: boolean
  toggle: () => void
}

function applyClass(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      dark: true,
      toggle: () => {
        const next = !get().dark
        applyClass(next)
        set({ dark: next })
      },
    }),
    {
      name: 'theme',
      version: 1,
      // Light mode did not exist before v1, so any value persisted earlier
      // was never a real choice. Force those users to dark; light is opt-in.
      migrate: (persisted, version) => {
        if (version < 1) return { dark: true } as ThemeState
        return persisted as ThemeState
      },
    },
  ),
)

export function initTheme() {
  applyClass(useThemeStore.getState().dark)
}
