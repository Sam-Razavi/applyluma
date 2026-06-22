// One-shot codemod: migrate hardcoded dark-only Tailwind utilities to the
// semantic theme tokens (bg-surface, text-fg, chip-*, accent, …) so both
// light and dark themes flip from the CSS variables in index.css.
//
// Run:  node scripts/migrate-theme-tokens.mjs
// Idempotent: already-migrated files are left unchanged.
import { readFileSync, writeFileSync } from 'node:fs'
import { execSync } from 'node:child_process'

// Collect target files via git (tracked) + plain glob fallback.
const files = execSync('git ls-files "frontend/src/**/*.tsx"', { encoding: 'utf8' })
  .split('\n')
  .map((s) => s.trim())
  .filter(Boolean)
  .filter((f) => !f.endsWith('.test.tsx'))

function opacityPct(token) {
  // token like "90" or "[0.55]" or "[.06]"
  if (token.startsWith('[')) {
    const inner = token.slice(1, -1)
    const v = parseFloat(inner)
    return v <= 1 ? Math.round(v * 100) : v
  }
  return parseInt(token, 10)
}

function textTier(pct) {
  if (pct >= 70) return 'text-fg'
  if (pct >= 45) return 'text-fg-muted'
  return 'text-fg-subtle'
}
function borderTier(pct) {
  return pct >= 15 ? 'border-line-strong' : 'border-line'
}

const OPACITY = '(\\[[0-9.]+\\]|[0-9]+)'

function convertLine(line) {
  let L = line

  // --- Tinted rgba literals → chip / accent tokens (any alpha) ---
  L = L.replace(/bg-\[rgba\(8,\s*145,\s*178,[^\])]+\)\]/g, 'bg-chip-accent')
  L = L.replace(/border-\[rgba\(8,\s*145,\s*178,[^\])]+\)\]/g, 'border-accent-muted')
  L = L.replace(/bg-\[rgba\(52,\s*195,\s*143,[^\])]+\)\]/g, 'bg-chip-success')
  L = L.replace(/border-\[rgba\(52,\s*195,\s*143,[^\])]+\)\]/g, 'border-chip-success')
  L = L.replace(/bg-\[rgba\(245,\s*158,\s*11,[^\])]+\)\]/g, 'bg-chip-warn')
  L = L.replace(/border-\[rgba\(245,\s*158,\s*11,[^\])]+\)\]/g, 'border-chip-warn')
  L = L.replace(/bg-\[rgba\(229,\s*72,\s*77,[^\])]+\)\]/g, 'bg-chip-danger')
  L = L.replace(/border-\[rgba\(229,\s*72,\s*77,[^\])]+\)\]/g, 'border-chip-danger')

  // --- Accent text/icon shades → accent-text ---
  L = L.replace(/\btext-cyan-(200|300|400|500)\b/g, 'text-accent-text')
  L = L.replace(/\btext-primary-(300|400)\b/g, 'text-accent-text')
  L = L.replace(/hover:text-primary-(200|300|400)\b/g, 'hover:opacity-80')
  L = L.replace(/group-hover:text-(primary|brand)-(300|400|500|700)\b/g, 'group-hover:text-accent-text')
  L = L.replace(/hover:text-(primary|brand)-(600|700)\b/g, 'hover:opacity-80')

  // --- Status text shades → chip foreground tokens ---
  L = L.replace(/\btext-emerald-(200|300|400)\b/g, 'text-chip-success-fg')
  L = L.replace(/\btext-green-(300|400)\b/g, 'text-chip-success-fg')
  L = L.replace(/\btext-amber-(200|300|400)\b/g, 'text-chip-warn-fg')
  L = L.replace(/\btext-yellow-(300|400)\b/g, 'text-chip-warn-fg')
  L = L.replace(/\btext-red-(300|400)\b/g, 'text-chip-danger-fg')
  L = L.replace(/\btext-rose-(300|400)\b/g, 'text-chip-danger-fg')

  // --- White text opacity tiers ---
  L = L.replace(new RegExp(`\\btext-white/${OPACITY}`, 'g'), (_, op) => textTier(opacityPct(op)))

  // --- Borders / dividers / rings ---
  L = L.replace(new RegExp(`\\bborder-white/${OPACITY}`, 'g'), (_, op) => borderTier(opacityPct(op)))
  L = L.replace(new RegExp(`\\bdivide-white/${OPACITY}`, 'g'), 'divide-line')
  L = L.replace(new RegExp(`\\bring-white/${OPACITY}`, 'g'), 'ring-line')

  // --- Gradient white stops ---
  L = L.replace(new RegExp(`\\bfrom-white/${OPACITY}`, 'g'), 'from-surface')
  L = L.replace(new RegExp(`\\bvia-white/${OPACITY}`, 'g'), 'via-surface')
  L = L.replace(new RegExp(`\\bto-white/${OPACITY}`, 'g'), 'to-surface')

  // --- Placeholder ---
  L = L.replace(new RegExp(`\\bplaceholder-white/${OPACITY}`, 'g'), 'placeholder-fg-subtle')

  // --- Hover backgrounds → stronger surface ---
  L = L.replace(new RegExp(`\\bhover:bg-white/${OPACITY}`, 'g'), 'hover:bg-surface-strong')

  // --- Plain white backgrounds: skeleton/track vs surface (line-level heuristic) ---
  const isTrack =
    /animate-pulse/.test(line) ||
    (/rounded-full/.test(line) && /overflow-hidden/.test(line)) ||
    /\bh-1(\.5)?\b/.test(line) // thin bar tracks
  const bgTok = isTrack ? 'bg-track' : 'bg-surface'
  L = L.replace(new RegExp(`\\bbg-white/${OPACITY}`, 'g'), bgTok)

  return L
}

let changed = 0
for (const file of files) {
  const orig = readFileSync(file, 'utf8')
  const out = orig.split('\n').map(convertLine).join('\n')
  if (out !== orig) {
    writeFileSync(file, out)
    changed++
    console.log('updated', file)
  }
}
console.log(`\n${changed} files updated of ${files.length} scanned.`)
