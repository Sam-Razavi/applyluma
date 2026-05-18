# ApplyLuma: Mobile Responsiveness & UX Enhancement Plan

## Context

The ApplyLuma frontend is functional but lacks mobile polish and smooth interactions. Three libraries are being introduced: `framer-motion` (animations), `react-use-gesture` (touch gestures), and `react-dropzone` (file uploads). This plan audits the current state, prioritizes issues, and produces five actionable documents for Codex-guided execution. The core principle: **additive enhancement only** — no desktop functionality regresses.

---

## ⚠️ Critical Prerequisite

**`framer-motion` and `react-use-gesture` are NOT in `package.json` yet.**

`react-dropzone` v15.0.0 is already installed. The other two need to be added before any Section 2+ work begins:

```bash
cd frontend
npm install framer-motion@^11.0.0 @use-gesture/react@^10.3.0
```

> Note: the modern package for react-use-gesture is `@use-gesture/react` (v10). The old `react-use-gesture` package is abandoned.

---

## Audit Findings

### Navigation (`components/layout/`)

| Issue | File | Line | Priority |
|-------|------|------|----------|
| Two competing mobile nav implementations | `Navbar.tsx` + `MobileNav.tsx` | — | P1 |
| Inline mobile dropdown has zero animation (instant show/hide) | `Navbar.tsx` | 169–189 | P1 |
| Hamburger button is ~30px (below 44px minimum) | `Navbar.tsx` | 152–165 | P1 |
| User avatar button is 32px (below 44px minimum) | `Navbar.tsx` | 111–113 | P1 |
| User dropdown `w-52` overflows on phones <280px | `Navbar.tsx` | 137 | P1 |
| MobileNav close button is 40px (just below 44px) | `MobileNav.tsx` | 39 | P2 |
| `AppLayout.tsx` main content missing `py-4` responsive padding | `AppLayout.tsx` | 34 | P2 |

**Current state:** `Navbar.tsx` renders a full inline mobile dropdown (lines 169–189, no animation). `MobileNav.tsx` is a full-screen slide-from-left overlay with CSS `transition-transform duration-300`. `AppLayout.tsx` calls `MobileNav` and also renders a separate mobile header. **Recommendation:** Consolidate to one implementation — keep `MobileNav.tsx` (better UX, has overlay), and remove the inline dropdown from `Navbar.tsx`.

---

### Job Discovery (`pages/Discover.tsx`, `components/discover/`)

| Issue | File | Line | Priority |
|-------|------|------|----------|
| 5 action buttons in a single flex row on mobile | `JobDetail.tsx` | 179–234 | P1 |
| Filter collapse toggle UX could be clearer | `JobFilters.tsx` | 44–58 | P2 |

**Current state:** Overall good. Discover page uses `lg:flex-row`, filters have internal mobile toggle, job cards use `flex flex-wrap`. The job detail modal uses `items-end` bottom-sheet on mobile and `sm:items-center` on tablet. The only real issue is the action button row getting cramped.

---

### Applications (`pages/Applications.tsx`, `components/applications/`)

| Issue | File | Line | Priority |
|-------|------|------|----------|
| `KanbanColumn` hard-coded `w-72 h-[calc(100vh-17rem)]` | `KanbanColumn.tsx` | 19 | P1 (desktop-only, hidden on mobile) |
| FAB `bottom-6 right-6` may overlap mobile system UI | `Applications.tsx` | 162–169 | P2 |

**Current state:** Exemplary. `KanbanBoard.tsx` has a full mobile redesign at `md:hidden` using accordion pattern. `ApplicationDrawer.tsx` slides from bottom on mobile, from right on desktop. `ApplicationStats.tsx` uses `grid-cols-2 sm:grid-cols-4 lg:grid-cols-7`. No critical issues.

---

### CVs / Resume Management (`pages/CVs.tsx`)

| Issue | File | Line | Priority |
|-------|------|------|----------|
| Upload input `w-44` fixed — doesn't wrap on mobile | `CVs.tsx` | 192 | P0 |
| Dropzone uses `p-10` (too much padding for small screens) | `CVs.tsx` | 159 | P1 |
| CV list action buttons `h-8 w-8` (32px, below 44px) | `CVs.tsx` | 294–340 | P1 |
| Upload/cancel buttons use `py-1.5` (short touch target) | `CVs.tsx` | 196, 203 | P1 |

**Current state:** `react-dropzone` is already integrated. The main issues are the fixed-width title input in the pending file row and small touch targets on action buttons.

---

### AI Tailor (`pages/AITailor.tsx`, `components/tailor/`)

| Issue | File | Line | Priority |
|-------|------|------|----------|
| `SectionDiff` two-column grid uses `lg:grid-cols-2` (should be `md:`) | `SectionDiff.tsx` | 33 | P0 |
| `VersionDiffViewer` `max-w-5xl` touches edges on tablets | `VersionDiffViewer.tsx` | 48 | P1 |

---

### Global / Cross-Cutting

| Issue | File | Line | Priority |
|-------|------|------|----------|
| `.input` class has `py-2` = ~36px (below 44px touch target) | `index.css` | 6–8 | P1 |
| No `framer-motion` animations anywhere (CSS-only) | `package.json` | — | P2 (enhancement) |
| No skeleton loading components | — | — | P2 (enhancement) |
| No `prefers-reduced-motion` handling | — | — | P2 |

---

## Implementation Plan

### Section 1 — Responsive Foundation & Touch Targets
**Scope:** Global fixes that unblock all other sections. No new dependencies required.

**Files to modify:**
- `frontend/src/index.css` — bump `.input` min-height to 44px
- `frontend/src/pages/CVs.tsx` — fix `w-44` input, `p-10` dropzone, `h-8 w-8` buttons
- `frontend/src/components/tailor/SectionDiff.tsx` — `lg:` → `md:` grid breakpoint
- `frontend/src/components/applications/KanbanColumn.tsx` — responsive min-height

**Key changes:**
```css
/* index.css — .input class */
min-height: 2.75rem; /* 44px */
```
```tsx
// CVs.tsx pending file row — line 192
className="... w-full sm:w-44 ..."

// CVs.tsx dropzone — line 159
className="... p-6 sm:p-10 ..."

// CVs.tsx action buttons — lines 294–340
className="... h-10 w-10 ..." /* was h-8 w-8 */
```
```tsx
// SectionDiff.tsx — line 33
className="grid md:grid-cols-2 md:divide-x" /* was lg:grid-cols-2 */
```

**Testing checklist:**
- [ ] 375px: CVs upload row wraps without overflow
- [ ] 375px: All action buttons at least 40×40px tap area
- [ ] 768px: SectionDiff shows 2 columns
- [ ] `npm run type-check` passes
- [ ] `npm test` 38/38 pass

---

### Section 2 — Navigation Consolidation + framer-motion Animation
**Scope:** Single mobile nav with smooth framer-motion animation. Requires framer-motion installed.

**Files to modify:**
- `frontend/src/components/layout/Navbar.tsx` — remove inline mobile dropdown (lines 169–189), fix touch targets
- `frontend/src/components/layout/MobileNav.tsx` — replace CSS transitions with framer-motion `AnimatePresence`
- `frontend/src/components/layout/AppLayout.tsx` — confirm MobileNav is sole mobile entry point

**Key changes:**
```tsx
// MobileNav.tsx — replace CSS slide with framer-motion
import { AnimatePresence, motion } from 'framer-motion'

export default function MobileNav({ open, onClose }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Overlay */}
          <motion.div
            key="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/30"
            onClick={onClose}
          />
          {/* Drawer */}
          <motion.nav
            key="drawer"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="absolute inset-y-0 left-0 flex w-72 flex-col bg-white shadow-2xl"
            aria-label="Mobile navigation"
          >
            {/* ... existing content ... */}
          </motion.nav>
        </div>
      )}
    </AnimatePresence>
  )
}
```

```tsx
// Navbar.tsx — bump hamburger button to 44px tap area
className="inline-flex items-center justify-center rounded-lg p-2.5 text-gray-600 ... md:hidden"
// h-5 w-5 icon + p-2.5 padding = 44px total

// Navbar.tsx — bump avatar button vertical padding
className="flex items-center gap-2 rounded-lg px-2 py-2 ..."
// was py-1.5

// Navbar.tsx — remove lines 169–189 (inline mobile dropdown)
// MobileNav (called via AppLayout) is the only mobile nav now
```

**Testing checklist:**
- [ ] 375px: Hamburger opens MobileNav drawer (not inline dropdown)
- [ ] Drawer slides in smoothly from left, overlay fades in
- [ ] Closing: overlay click, Escape key, X button all work
- [ ] Touch targets ≥44px on hamburger and avatar
- [ ] No duplicate nav on any breakpoint
- [ ] `npm test` 38/38 pass

---

### Section 3 — Job Discovery UX
**Scope:** Fix crowded action buttons in JobDetail, add stagger animation to job card list, optional swipe gesture.

**Files to modify:**
- `frontend/src/components/discover/JobDetail.tsx` — responsive action button row
- `frontend/src/pages/Discover.tsx` — stagger animation on job card list
- `frontend/src/components/discover/JobCard.tsx` — optional: swipe-to-save gesture

**Key changes:**
```tsx
// JobDetail.tsx action buttons — lines 179–234
// Wrap action buttons to stack on mobile
<div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-4 border-t border-gray-100">
  {/* Save, Tailor CV, Add to Tracker, Apply Now buttons */}
</div>
```

```tsx
// Discover.tsx — stagger job cards with framer-motion
import { motion } from 'framer-motion'

{jobs.map((job, i) => (
  <motion.div
    key={job.id}
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: i * 0.04, duration: 0.2 }}
  >
    <JobCard job={job} />
  </motion.div>
))}
```

**Optional — swipe-to-save on JobCard (`@use-gesture/react`):**
```tsx
import { useDrag } from '@use-gesture/react'
import { useSpring, animated } from '@react-spring/web' // or framer-motion useMotionValue

const [{ x }, api] = useSpring(() => ({ x: 0 }))
const bind = useDrag(
  ({ movement: [mx], last, velocity: [vx] }) => {
    if (last) {
      if (mx > 80 || vx > 0.5) { onSave(job.id); api.start({ x: 0 }) }
      else if (mx < -80 || vx < -0.5) { onDismiss(job.id); api.start({ x: 0 }) }
      else { api.start({ x: 0 }) }
    } else {
      api.start({ x: mx, immediate: true })
    }
  },
  { axis: 'x', filterTaps: true }
)
```

**Testing checklist:**
- [ ] 375px: JobDetail action buttons stack vertically (1 per row)
- [ ] 768px: Action buttons in a single row
- [ ] Job cards animate in with stagger on initial load and pagination
- [ ] Animation respects `prefers-reduced-motion`

---

### Section 4 — Resume Upload & Management Polish
**Scope:** `react-dropzone` is already integrated. Add framer-motion animated progress bar, improve mobile layout.

**Files to modify:**
- `frontend/src/pages/CVs.tsx` — animated progress bar, layout fixes (complement Section 1 fixes)

**Key changes:**
```tsx
// CVs.tsx — animated upload progress bar (replace static div)
import { motion } from 'framer-motion'

<div className="h-2 bg-gray-100 rounded-full overflow-hidden">
  <motion.div
    className="h-full bg-brand-500 rounded-full"
    initial={{ width: 0 }}
    animate={{ width: `${uploadPct}%` }}
    transition={{ ease: 'linear', duration: 0.1 }}
  />
</div>
```

```tsx
// CVs.tsx — pending file row: ensure flex-wrap works with full-width input on mobile
// (w-44 → w-full sm:w-44 already done in Section 1)
// Also: bump upload button height
className="... px-4 py-2.5 ..." /* was py-1.5 — now 44px touch target */
```

**Testing checklist:**
- [ ] 375px: Pending file row wraps cleanly (filename + input + buttons all accessible)
- [ ] Upload progress bar animates smoothly
- [ ] Drag-and-drop still works on desktop
- [ ] Tap-to-browse works on iOS Safari and Android Chrome

---

### Section 5 — AI Tailor Mobile Experience
**Scope:** Fix grid breakpoints (Section 1 already handles the P0), add smooth expand/collapse animation to section diff panels.

**Files to modify:**
- `frontend/src/components/tailor/SectionDiff.tsx` — animated panel expand (breakpoint fix done in Section 1)
- `frontend/src/pages/AITailor.tsx` — step transition animation

**Key changes:**
```tsx
// SectionDiff.tsx — animate section expand/collapse
import { AnimatePresence, motion } from 'framer-motion'

<AnimatePresence initial={false}>
  {isExpanded && (
    <motion.div
      key="diff-content"
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      style={{ overflow: 'hidden' }}
    >
      {/* diff content */}
    </motion.div>
  )}
</AnimatePresence>
```

```tsx
// AITailor.tsx — animate step transitions
<AnimatePresence mode="wait">
  <motion.div
    key={currentStep}
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    transition={{ duration: 0.2 }}
  >
    {/* current step content */}
  </motion.div>
</AnimatePresence>
```

**Testing checklist:**
- [ ] 768px: SectionDiff shows 2-column layout (from Section 1 fix)
- [ ] 375px: Sections expand/collapse with smooth animation
- [ ] AI Tailor steps transition smoothly
- [ ] No layout shift during animations

---

### Section 6 — Micro-interactions & Polish
**Scope:** Button press feedback, page fade-ins, skeleton loading screens, `prefers-reduced-motion` support.

**Files to create:**
- `frontend/src/components/ui/FadeIn.tsx` — reusable page/section fade-in wrapper
- `frontend/src/components/ui/SkeletonCard.tsx` — shimmer skeleton for job card loading states

**Files to modify:**
- `frontend/src/index.css` — add `prefers-reduced-motion` block
- `frontend/src/pages/Discover.tsx` — use `SkeletonCard` during initial load
- `frontend/src/App.tsx` or route entry components — wrap pages with `FadeIn`

**Key changes:**
```tsx
// frontend/src/components/ui/FadeIn.tsx
import { motion } from 'framer-motion'

export function FadeIn({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay }}
    >
      {children}
    </motion.div>
  )
}
```

```tsx
// frontend/src/components/ui/SkeletonCard.tsx
export function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-gray-100 bg-white p-5 space-y-3">
      <div className="h-4 bg-gray-200 rounded w-3/4" />
      <div className="h-3 bg-gray-200 rounded w-1/2" />
      <div className="h-3 bg-gray-200 rounded w-2/3" />
      <div className="flex gap-2 pt-2">
        <div className="h-6 bg-gray-200 rounded-full w-16" />
        <div className="h-6 bg-gray-200 rounded-full w-20" />
      </div>
    </div>
  )
}
```

```css
/* frontend/src/index.css */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

**Testing checklist:**
- [ ] Pages fade in on navigation (no jarring instant render)
- [ ] Job cards show skeletons during initial Discover load
- [ ] On macOS/iOS with "Reduce Motion" enabled: no animations play
- [ ] `npm run build` bundle size increase < 50KB vs baseline

---

### Section 7 — Advanced Gestures (Optional / Future)
Defer until Sections 1–6 validated in production.

- Pull-to-refresh on Discover feed
- Pinch-to-zoom on CV PDF preview
- Swipe navigation between job details in a carousel

---

## Animation Design System

### Core Constants (`frontend/src/lib/animations.ts` — create this file)
```ts
export const spring = {
  snappy: { type: 'spring', damping: 30, stiffness: 300 },
  gentle: { type: 'spring', damping: 25, stiffness: 200 },
}

export const ease = {
  quick:    { duration: 0.15 },
  standard: { duration: 0.25 },
  slow:     { duration: 0.4 },
}

export const staggerItem = (i: number) => ({ delay: i * 0.04, duration: 0.2 })

export const variants = {
  fadeIn:     { initial: { opacity: 0 },          animate: { opacity: 1 } },
  slideUp:    { initial: { opacity: 0, y: 16 },   animate: { opacity: 1, y: 0 } },
  slideLeft:  { initial: { x: '-100%' },           animate: { x: 0 } },
  slideRight: { initial: { x: '100%' },            animate: { x: 0 } },
  scaleIn:    { initial: { opacity: 0, scale: 0.95 }, animate: { opacity: 1, scale: 1 } },
}
```

### Gesture Thresholds
```ts
// Swipe: fire at 80px displacement OR velocity > 0.5px/ms
export const SWIPE_THRESHOLD_PX = 80
export const SWIPE_VELOCITY = 0.5

// Drag-to-close: fire when dragged down past 40% of element height
export const DRAG_CLOSE_RATIO = 0.4
```

### Performance Rules
- Animate only `opacity` and `transform` (translate/scale/rotate) — GPU-accelerated
- Never animate `width`, `height`, `margin`, `padding` — causes layout reflow
- For height animations use `height: 'auto'` with `AnimatePresence` and `overflow: hidden`
- `will-change: transform` only on elements that animate on every frame (e.g., drag)
- All exit animations require `AnimatePresence` wrapper

---

## Codex Execution Prompts

### Prompt 1: Responsive Foundation & Touch Targets

**Objective:** Fix all P0 and core P1 responsive issues with no new dependencies.

**Files to modify:**
- `frontend/src/index.css`
- `frontend/src/pages/CVs.tsx`
- `frontend/src/components/tailor/SectionDiff.tsx`

**Steps:**
1. In `index.css`, add `min-height: 2.75rem;` to the `.input` class.
2. In `CVs.tsx` line 192, change `w-44` to `w-full sm:w-44` on the title input.
3. In `CVs.tsx` line 159, change `p-10` to `p-6 sm:p-10` on the dropzone div.
4. In `CVs.tsx`, find all `h-8 w-8` icon buttons in the CV list and change to `h-10 w-10`. These are the view, download, history, star, and delete buttons.
5. In `CVs.tsx` upload button (line 197), change `py-1.5` to `py-2.5`.
6. In `SectionDiff.tsx` line 33, change `lg:grid-cols-2 lg:divide-x` to `md:grid-cols-2 md:divide-x`.

**Testing checklist:**
- [ ] 375px: CVs upload pending row wraps without overflow
- [ ] 375px: Dropzone visible and tappable
- [ ] 768px: SectionDiff shows 2-column layout
- [ ] `npm run type-check` — 0 errors
- [ ] `npm test` — 38/38 pass

**Completion criteria:** All P0 issues resolved. No TypeScript errors. All tests pass.

---

### Prompt 2: Navigation Consolidation + framer-motion

**Prerequisite:** `framer-motion` installed (`npm install framer-motion@^11.0.0`).

**Objective:** Replace the Navbar inline mobile dropdown with the existing `MobileNav.tsx` overlay, add framer-motion animation to the drawer, fix touch targets.

**Files to modify:**
- `frontend/src/components/layout/Navbar.tsx`
- `frontend/src/components/layout/MobileNav.tsx`

**Steps:**
1. In `MobileNav.tsx`:
   - Import `AnimatePresence` and `motion` from `framer-motion`.
   - Remove the conditional `className` toggle pattern on the outer div, overlay div, and nav element.
   - Wrap the entire drawer in `<AnimatePresence>`. Only render children when `open` is true.
   - Replace overlay `<div>` with `<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>`.
   - Replace nav `<nav>` with `<motion.nav initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'spring', damping: 30, stiffness: 300 }}>`. Remove all `translate-x` CSS classes.
   - Remove the `pointer-events-none/auto` logic from the outer wrapper — it is no longer needed since `AnimatePresence` unmounts on exit.
   - Bump close button to `h-11 w-11` (was `h-10 w-10`).

2. In `Navbar.tsx`:
   - Delete lines 169–189 (the `{mobileMenuOpen && <nav>...</nav>}` block entirely).
   - Remove the `mobileMenuRef` ref (no longer needed).
   - On the hamburger button (line 152–165), change `p-2` to `p-2.5` for 44px tap area.
   - On the user avatar button (line 111–113), change `py-1.5` to `py-2`.
   - The `mobileMenuOpen` state and its handlers remain — `AppLayout.tsx` wires `mobileMenuOpen` to `MobileNav`. Confirm `AppLayout.tsx` passes `open={mobileMenuOpen}` and `onClose` to `MobileNav`.

**Testing checklist:**
- [ ] 375px: Hamburger opens the slide-out MobileNav drawer (not an inline dropdown)
- [ ] Drawer slides in from left, overlay fades in simultaneously
- [ ] Overlay click, X button, and Escape key all close the drawer
- [ ] No duplicate navigation items visible at any breakpoint
- [ ] Hamburger button tap area ≥44px
- [ ] `npm test` — 38/38 pass

---

### Prompt 3: Job Discovery UX

**Prerequisite:** framer-motion installed.

**Objective:** Fix JobDetail action button crowding on mobile. Add stagger load animation to Discover job list.

**Files to modify:**
- `frontend/src/components/discover/JobDetail.tsx`
- `frontend/src/pages/Discover.tsx`

**Steps:**
1. In `JobDetail.tsx`, locate the action button row (lines 179–234). Wrap all buttons in a `<div className="flex flex-col sm:flex-row gap-2 sm:gap-3">`. Each button should be `w-full sm:w-auto`.
2. In `Discover.tsx`, import `motion` from `framer-motion`. Wrap each job card in the `.map()` with:
   ```tsx
   <motion.div
     key={job.id}
     initial={{ opacity: 0, y: 16 }}
     animate={{ opacity: 1, y: 0 }}
     transition={{ delay: index * 0.04, duration: 0.2 }}
   >
   ```
   Only apply stagger when `jobs` array length changes (initial load and pagination append), not on filter-only re-renders.

**Testing checklist:**
- [ ] 375px: JobDetail action buttons stack vertically, each full width
- [ ] 768px: Action buttons display in a single row
- [ ] Job cards animate in with stagger on first load
- [ ] Stagger animation doesn't replay on filter changes (only new results)
- [ ] `npm test` — 38/38 pass

---

### Prompt 4: Resume Upload Polish

**Prerequisite:** framer-motion installed.

**Objective:** Animated upload progress bar. This section's layout fixes were already done in Section 1.

**Files to modify:**
- `frontend/src/pages/CVs.tsx`

**Steps:**
1. Import `motion` from `framer-motion`.
2. Locate the upload progress bar div (line ~219):
   ```tsx
   <div className="h-full bg-brand-500 rounded-full transition-all duration-200" style={{ width: `${uploadPct}%` }} />
   ```
   Replace with:
   ```tsx
   <motion.div
     className="h-full bg-brand-500 rounded-full"
     initial={{ width: 0 }}
     animate={{ width: `${uploadPct}%` }}
     transition={{ ease: 'linear', duration: 0.1 }}
   />
   ```
   Remove the `transition-all duration-200` Tailwind class since framer-motion handles the transition.

**Testing checklist:**
- [ ] Upload progress bar animates smoothly from 0 to 100%
- [ ] No visual regression on drag-and-drop desktop upload
- [ ] Tap-to-upload works on mobile (iOS Safari)

---

### Prompt 5: AI Tailor Mobile Experience

**Prerequisite:** framer-motion installed. Section 1 grid fix already applied.

**Objective:** Animate section diff panel expand/collapse. Add step transition in AITailor wizard.

**Files to modify:**
- `frontend/src/components/tailor/SectionDiff.tsx`
- `frontend/src/pages/AITailor.tsx`

**Steps:**
1. In `SectionDiff.tsx`, find the conditional render of the diff panel content. Import `AnimatePresence` and `motion`. Wrap the conditional block:
   ```tsx
   <AnimatePresence initial={false}>
     {isExpanded && (
       <motion.div
         key="content"
         initial={{ height: 0, opacity: 0 }}
         animate={{ height: 'auto', opacity: 1 }}
         exit={{ height: 0, opacity: 0 }}
         transition={{ duration: 0.2, ease: 'easeInOut' }}
         style={{ overflow: 'hidden' }}
       >
         {/* existing diff content */}
       </motion.div>
     )}
   </AnimatePresence>
   ```

2. In `AITailor.tsx`, find where the current step component is rendered. Wrap with:
   ```tsx
   <AnimatePresence mode="wait">
     <motion.div
       key={currentStep}
       initial={{ opacity: 0, x: 20 }}
       animate={{ opacity: 1, x: 0 }}
       exit={{ opacity: 0, x: -20 }}
       transition={{ duration: 0.18 }}
     >
       {/* step content */}
     </motion.div>
   </AnimatePresence>
   ```

**Testing checklist:**
- [ ] 375px: Expanding a diff section animates height smoothly
- [ ] No content jump or flash during expand/collapse
- [ ] AITailor wizard steps slide left/right on navigation
- [ ] `npm test` — 38/38 pass

---

### Prompt 6: Micro-interactions & Global Polish

**Prerequisite:** framer-motion installed. Sections 1–5 complete.

**Objective:** Skeleton loading, page fade-ins, `prefers-reduced-motion` support.

**Files to create:**
- `frontend/src/components/ui/FadeIn.tsx`
- `frontend/src/components/ui/SkeletonCard.tsx`
- `frontend/src/lib/animations.ts`

**Files to modify:**
- `frontend/src/index.css`
- `frontend/src/pages/Discover.tsx` — use `SkeletonCard` while loading
- 2–3 key page entry points — wrap content in `<FadeIn>`

**Steps:**
1. Create `frontend/src/lib/animations.ts` with the spring, ease, staggerItem, and variants constants from the Animation Design System section above.

2. Create `frontend/src/components/ui/FadeIn.tsx`:
   ```tsx
   import { motion } from 'framer-motion'
   export function FadeIn({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
     return (
       <motion.div
         initial={{ opacity: 0, y: 8 }}
         animate={{ opacity: 1, y: 0 }}
         transition={{ duration: 0.25, delay }}
       >
         {children}
       </motion.div>
     )
   }
   ```

3. Create `frontend/src/components/ui/SkeletonCard.tsx` (code in Section 6 above).

4. In `index.css`, add the `@media (prefers-reduced-motion: reduce)` block at the bottom of the file.

5. In `Discover.tsx`, while `isLoading` is true and `jobs.length === 0`, render 6 `<SkeletonCard />` components instead of the empty state or nothing.

6. Wrap the top-level content div in `Dashboard.tsx` and `Discover.tsx` with `<FadeIn>`.

**Testing checklist:**
- [ ] Discover shows skeleton cards on first load before jobs arrive
- [ ] Dashboard fades in on navigation
- [ ] On macOS "Reduce Motion" setting: no animations play (verify with DevTools emulation)
- [ ] `npm run build` — note bundle size delta (target: <50KB increase)
- [ ] `npm test` — 38/38 pass

---

## Verification Plan

After each section:

| Step | Command | Expected |
|------|---------|----------|
| Type check | `cd frontend && npm run type-check` | 0 errors |
| Tests | `cd frontend && npm test` | 38/38 pass |
| Build | `cd frontend && npm run build` | 0 errors |
| Manual: 375px | Chrome DevTools → iPhone SE | No overflow, all buttons tappable |
| Manual: 768px | Chrome DevTools → iPad | Layouts correct at tablet breakpoint |
| Manual: 1024px | Chrome DevTools → desktop | No regressions |

**After Section 6 only — Lighthouse mobile audit:**
- Performance: ≥80
- Accessibility: ≥90
- Best Practices: ≥90

---

## Execution Order

```
0. npm install framer-motion@^11.0.0 @use-gesture/react@^10.3.0
1. Section 1 — Foundation fixes (no new deps, unblocks everything)
2. Section 2 — Navigation (first visible win)
3. Section 3 — Discover UX
4. Section 4 — CV Upload polish
5. Section 5 — AI Tailor
6. Section 6 — Global polish layer
7. Full test suite + type-check + build
8. Merge to dev → test on staging → merge to main
```

## Critical Files Reference

| Path | What to Change |
|------|----------------|
| `frontend/src/index.css` | Add `min-height: 2.75rem` to `.input`; add `prefers-reduced-motion` block |
| `frontend/src/components/layout/Navbar.tsx` | Remove inline mobile dropdown; fix touch targets |
| `frontend/src/components/layout/MobileNav.tsx` | Replace CSS transitions with framer-motion `AnimatePresence` |
| `frontend/src/pages/CVs.tsx` | Fix `w-44` → `w-full sm:w-44`; `p-10` → `p-6 sm:p-10`; `h-8` → `h-10` buttons; animated progress bar |
| `frontend/src/components/tailor/SectionDiff.tsx` | `lg:grid-cols-2` → `md:grid-cols-2`; animated expand |
| `frontend/src/components/discover/JobDetail.tsx` | Stack action buttons on mobile |
| `frontend/src/pages/Discover.tsx` | Stagger animation + skeleton loading |
| `frontend/src/pages/AITailor.tsx` | Step transition animation |
| `frontend/src/lib/animations.ts` | Create — shared animation constants |
| `frontend/src/components/ui/FadeIn.tsx` | Create — reusable fade-in wrapper |
| `frontend/src/components/ui/SkeletonCard.tsx` | Create — shimmer skeleton |
| `frontend/package.json` | Add framer-motion + @use-gesture/react |
