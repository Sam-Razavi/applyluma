import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { tailorApi } from '../services/tailorApi'
import { coverLetterApi } from '../services/coverLetterApi'
import type { TailorUsage } from '../types/tailor'
import type { CoverLetterUsage } from '../types/coverLetter'

interface UsageState {
  tailorUsage: TailorUsage | null
  coverUsage: CoverLetterUsage | null
  loaded: boolean
  loading: boolean
  // Fetch daily tailor + cover-letter usage once and cache it. Many job-ad
  // cards mount at once, so repeat calls are skipped unless `force` is set.
  loadUsage: (force?: boolean) => Promise<void>
}

type UsageLike = { used_today: number; daily_limit: number | null } | null

// A feature is "at limit" only when it has a finite daily cap that's been hit.
// Admins/premium with `daily_limit === null` are never at limit.
export function atLimit(usage: UsageLike): boolean {
  return !!usage && usage.daily_limit != null && usage.used_today >= usage.daily_limit
}

// Non-blocking hint for the combined "Tailor CV + Cover Letter" action.
// Returns null when nothing is capped (no hint shown).
export function usageHint(tailorUsage: UsageLike, coverUsage: UsageLike): string | null {
  const cvAtLimit = atLimit(tailorUsage)
  const coverAtLimit = atLimit(coverUsage)
  if (cvAtLimit && coverAtLimit) return 'Daily limits reached — try again after they reset.'
  if (cvAtLimit) return 'Daily CV tailor limit reached — you can still write a cover letter.'
  if (coverAtLimit) return 'Daily cover-letter limit reached — you can still tailor your CV.'
  return null
}

export const useUsageStore = create<UsageState>()(
  devtools(
    (set, get) => ({
      tailorUsage: null,
      coverUsage: null,
      loaded: false,
      loading: false,

      loadUsage: async (force = false) => {
        const { loaded, loading } = get()
        if (loading || (loaded && !force)) return
        set({ loading: true })
        try {
          const [tailorUsage, coverUsage] = await Promise.all([
            tailorApi.getUsage(),
            coverLetterApi.getUsage(),
          ])
          set({ tailorUsage, coverUsage, loaded: true, loading: false })
        } catch {
          // Usage is a non-critical hint; fail silently and let callers behave
          // as if no limit info is available.
          set({ loading: false })
        }
      },
    }),
    { name: 'UsageStore' },
  ),
)
