export type DescriptionBlock =
  | { kind: 'paragraph'; text: string }
  | { kind: 'heading'; text: string }
  | { kind: 'bullet'; items: string[] }
  | { kind: 'numbered'; items: string[] }

// Sentence boundaries followed by known job-description section headers
const SECTION_SPLIT_RE =
  /(?<=[.!?])\s+(?=(?:Responsibilities|Requirements|Qualifications|What you|About us|Who we|Nice to have|Benefits|We offer|The role|Your role|The team)\b)/gi

// Bullet prefix: hyphen, Unicode bullet (U+2022), or asterisk
const BULLET_LINE_RE = /^[-•*] /
const NUMBERED_LINE_RE = /^\d+[.)]\s/

/** Strip HTML tags. Fast-path skips parsing when no tags present. */
function stripHtml(text: string): string {
  if (!text.includes('<')) return text
  if (typeof document !== 'undefined') {
    const doc = new DOMParser().parseFromString(text, 'text/html')
    return doc.body.textContent ?? ''
  }
  return text.replace(/<[^>]+>/g, ' ')
}

/** Decode common HTML entities. */
function decodeEntities(text: string): string {
  return text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&#\d+;/g, ' ')
}

/**
 * Classify a single paragraph-level chunk of text into a typed block.
 * A chunk uses single `\n` between lines; blocks are separated by `\n\n`.
 */
function classifyChunk(chunk: string): DescriptionBlock {
  const lines = chunk.split('\n').filter(l => l.trim().length > 0)
  if (lines.length === 0) return { kind: 'paragraph', text: '' }

  // Single short line without sentence-ending punctuation → heading
  if (lines.length === 1 && lines[0].length <= 60 && !/[.!?]$/.test(lines[0])) {
    return { kind: 'heading', text: lines[0] }
  }

  if (lines.every(l => BULLET_LINE_RE.test(l))) {
    return {
      kind: 'bullet',
      items: lines.map(l => l.replace(BULLET_LINE_RE, '').trim()),
    }
  }

  if (lines.every(l => NUMBERED_LINE_RE.test(l))) {
    return {
      kind: 'numbered',
      items: lines.map(l => l.replace(NUMBERED_LINE_RE, '').trim()),
    }
  }

  return { kind: 'paragraph', text: lines.join(' ') }
}

/** Parse text that has meaningful newlines or bullet markers. */
function parseStructured(text: string): DescriptionBlock[] {
  return text
    .split(/\n{2,}/)
    .map(c => c.trim())
    .filter(Boolean)
    .map(classifyChunk)
    .filter(b => !(b.kind === 'paragraph' && b.text.length === 0))
}

/** Best-effort paragraph splitting for collapsed plain-text blobs. */
function parseBlob(text: string): DescriptionBlock[] {
  // Try splitting on sentence boundaries before known section headers
  const segments = text.split(SECTION_SPLIT_RE).map(s => s.trim()).filter(Boolean)
  if (segments.length >= 2) {
    return segments.map(s => ({ kind: 'paragraph' as const, text: s }))
  }

  // Fall back: split every ~350 chars at the nearest sentence boundary
  const blocks: DescriptionBlock[] = []
  let remaining = text.trim()
  const TARGET = 350

  while (remaining.length > TARGET) {
    const window = remaining.slice(0, TARGET + 100)
    const match = [...window.matchAll(/[.!?]\s/g)].filter(m => (m.index ?? 0) <= TARGET).pop()
    const cutAt = match ? (match.index ?? TARGET) + 1 : TARGET
    blocks.push({ kind: 'paragraph', text: remaining.slice(0, cutAt).trim() })
    remaining = remaining.slice(cutAt).trim()
  }

  if (remaining.length > 0) blocks.push({ kind: 'paragraph', text: remaining })

  return blocks
}

/**
 * Parse a raw job description string into structured blocks for display.
 * Handles both well-structured text (with newlines/bullets, e.g. from the
 * improved scraper) and collapsed blobs (existing jobs where HTML structure
 * was lost at scrape time).
 */
export function parseJobDescription(raw: string): DescriptionBlock[] {
  if (!raw || !raw.trim()) return []

  let text = stripHtml(raw)
  text = decodeEntities(text)
  text = text.trim()

  if (!text) return []

  // Detect structural signals BEFORE applying any short-circuit
  const newlineCount = (text.match(/\n/g) ?? []).length
  const hasBulletMarkers = text.includes('• ') || /^[-*] /m.test(text)
  const hasStructure = newlineCount >= 2 || hasBulletMarkers

  // Very short text with no structure → single paragraph, no splitting needed
  if (text.length < 100 && !hasStructure) {
    return [{ kind: 'paragraph', text }]
  }

  if (hasStructure) return parseStructured(text)

  return parseBlob(text)
}
