import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
  dark: boolean
  toggle: () => void
}

function applyClass(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
  // Keep the mobile browser chrome in step with the page background.
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', dark ? '#080E12' : '#E7ECF2')
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
    {
      name: 'theme',
      version: 2,
      // v1 persisted only on an explicit toggle, but light was not the default
      // then. Reset once so everyone starts in light; they can switch back
      // with the toggle (their choice is stored again from there).
      migrate: (persisted, version) => {
        if (version < 2) return { dark: false } as ThemeState
        return persisted as ThemeState
      },
    },
  ),
)

export function initTheme() {
  applyClass(useThemeStore.getState().dark)
}
