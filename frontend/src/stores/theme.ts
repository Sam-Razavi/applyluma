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
      dark: false,
      toggle: () => {
        const next = !get().dark
        applyClass(next)
        set({ dark: next })
      },
    }),
    { name: 'theme' },
  ),
)

export function initTheme() {
  applyClass(useThemeStore.getState().dark)
}
