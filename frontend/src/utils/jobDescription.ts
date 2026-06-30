export type DescriptionBlock =
  | { kind: 'paragraph'; text: string }
  | { kind: 'heading'; text: string }
  | { kind: 'bullet'; items: string[] }
  | { kind: 'numbered'; items: string[] }

// Known job-description section header phrases, used to split sentence-glued
// blobs and to detect headings even when no newline separates them from the
// surrounding prose. Longer/more-specific phrases first so the regex prefers
// them over their shorter substrings (e.g. "Din bakgrund och kompetens"
// before "Din bakgrund").
const ENGLISH_SECTION_WORDS = [
  'Responsibilities', 'Requirements', 'Qualifications', 'What you',
  'About us', 'Who we', 'Nice to have', 'Benefits', 'We offer',
  'The role', 'Your role', 'The team',
]

const SWEDISH_SECTION_WORDS = [
  'Dina arbetsuppgifter', 'Arbetsuppgifter',
  'Din bakgrund och kompetens', 'Bakgrund och kompetens', 'Din bakgrund',
  'Dina kvalifikationer', 'Kvalifikationer',
  'Det är meriterande', 'Meriterande',
  'Dina personliga egenskaper', 'Personliga egenskaper',
  'Vårt erbjudande', 'Vi erbjuder dig',
  'Om tjänsten', 'Om oss', 'Om rollen',
  'Ansök senast', 'Så ansöker du',
]

const SECTION_WORDS = [...ENGLISH_SECTION_WORDS, ...SWEDISH_SECTION_WORDS]

// Sentence boundaries followed by a known job-description section header
const SECTION_SPLIT_RE = new RegExp(
  `(?<=[.!?])\\s+(?=(?:${SECTION_WORDS.join('|')})\\b)`,
  'gi'
)

// Stricter subset used for heading extraction — excludes phrases that also
// occur as ordinary mid-sentence openers in real job ad text (e.g. "Vi
// erbjuder dig" appears both as a section header and as a normal sentence
// start, so it is only used for section splitting, not heading detection).
const HEADING_WORDS = [
  'Dina arbetsuppgifter', 'Arbetsuppgifter',
  'Din bakgrund och kompetens', 'Dina kvalifikationer', 'Kvalifikationer',
  'Det är meriterande', 'Dina personliga egenskaper',
  'Vårt erbjudande', 'Om tjänsten',
  'Ansök senast',
  'Responsibilities', 'Requirements', 'Qualifications',
  'About us', 'Benefits', 'The role', 'Your role',
]

const HEADING_SPLIT_RE = new RegExp(`^(${HEADING_WORDS.join('|')})\\b[:\\s]*`, 'i')

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

/** Split text on sentence boundaries that precede a known section header. */
function splitSections(text: string): string[] {
  const segments = text.split(SECTION_SPLIT_RE).map(s => s.trim()).filter(Boolean)
  return segments.length >= 2 ? segments : [text]
}

/** Split a long blob every ~target chars at the nearest sentence boundary. */
function chunkBySentence(text: string, target = 350): string[] {
  const chunks: string[] = []
  let remaining = text.trim()

  while (remaining.length > target) {
    const window = remaining.slice(0, target + 100)
    const match = [...window.matchAll(/[.!?]\s/g)].filter(m => (m.index ?? 0) <= target).pop()
    const cutAt = match ? (match.index ?? target) + 1 : target
    chunks.push(remaining.slice(0, cutAt).trim())
    remaining = remaining.slice(cutAt).trim()
  }

  if (remaining.length > 0) chunks.push(remaining)

  return chunks
}

/**
 * If a segment opens with a recognized section-header phrase, split it into
 * a heading block plus the remaining paragraph text.
 */
function splitLeadingHeading(segment: string): DescriptionBlock[] {
  const match = segment.match(HEADING_SPLIT_RE)
  if (!match) return [{ kind: 'paragraph', text: segment }]

  const heading: DescriptionBlock = { kind: 'heading', text: match[1] }
  const rest = segment.slice(match[0].length).trim()

  return rest ? [heading, { kind: 'paragraph', text: rest }] : [heading]
}

/** Break an unstructured paragraph into heading/paragraph blocks. */
function splitLongParagraph(text: string): DescriptionBlock[] {
  return splitSections(text)
    .flatMap(splitLeadingHeading)
    .flatMap(block =>
      block.kind === 'paragraph' && block.text.length > 450
        ? chunkBySentence(block.text).map(c => ({ kind: 'paragraph' as const, text: c }))
        : [block]
    )
}

/**
 * Classify a single paragraph-level chunk of text into one or more typed
 * blocks. A chunk uses single `\n` between lines; blocks are separated by
 * `\n\n`.
 */
function classifyChunk(chunk: string): DescriptionBlock[] {
  const lines = chunk.split('\n').filter(l => l.trim().length > 0)
  if (lines.length === 0) return [{ kind: 'paragraph', text: '' }]

  // Single short line without sentence-ending punctuation → heading
  if (lines.length === 1 && lines[0].length <= 60 && !/[.!?]$/.test(lines[0])) {
    return [{ kind: 'heading', text: lines[0] }]
  }

  if (lines.every(l => BULLET_LINE_RE.test(l))) {
    return [{
      kind: 'bullet',
      items: lines.map(l => l.replace(BULLET_LINE_RE, '').trim()),
    }]
  }

  if (lines.every(l => NUMBERED_LINE_RE.test(l))) {
    return [{
      kind: 'numbered',
      items: lines.map(l => l.replace(NUMBERED_LINE_RE, '').trim()),
    }]
  }

  return splitLongParagraph(lines.join(' '))
}

/**
 * Fallback for text whose sections are separated by single `\n` rather than
 * `\n\n` (no blank-line paragraph breaks). Groups consecutive bullet/numbered
 * lines into list blocks; every other line is classified individually.
 */
function parseLineByLine(text: string): DescriptionBlock[] {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0)
  const blocks: DescriptionBlock[] = []
  let bulletBuf: string[] = []
  let numberedBuf: string[] = []

  const flushBullet = () => {
    if (bulletBuf.length > 0) {
      blocks.push({ kind: 'bullet', items: bulletBuf.map(l => l.replace(BULLET_LINE_RE, '').trim()) })
      bulletBuf = []
    }
  }
  const flushNumbered = () => {
    if (numberedBuf.length > 0) {
      blocks.push({ kind: 'numbered', items: numberedBuf.map(l => l.replace(NUMBERED_LINE_RE, '').trim()) })
      numberedBuf = []
    }
  }

  for (const line of lines) {
    if (BULLET_LINE_RE.test(line)) {
      flushNumbered()
      bulletBuf.push(line)
    } else if (NUMBERED_LINE_RE.test(line)) {
      flushBullet()
      numberedBuf.push(line)
    } else {
      flushBullet()
      flushNumbered()
      blocks.push(...classifyChunk(line))
    }
  }
  flushBullet()
  flushNumbered()

  return blocks.filter(b => !(b.kind === 'paragraph' && b.text.length === 0))
}

/** Parse text that has meaningful newlines or bullet markers. */
function parseStructured(text: string): DescriptionBlock[] {
  const chunks = text
    .split(/\n{2,}/)
    .map(c => c.trim())
    .filter(Boolean)

  // No blank-line paragraph breaks found, but single newlines exist: the
  // source likely separates sections with one `\n` instead of two.
  if (chunks.length <= 1 && text.includes('\n')) {
    return parseLineByLine(text)
  }

  return chunks
    .flatMap(classifyChunk)
    .filter(b => !(b.kind === 'paragraph' && b.text.length === 0))
}

/** Best-effort paragraph splitting for collapsed plain-text blobs. */
function parseBlob(text: string): DescriptionBlock[] {
  const segments = splitSections(text)
  if (segments.length >= 2) {
    return segments.flatMap(s =>
      s.length > 450
        ? chunkBySentence(s).map(c => ({ kind: 'paragraph' as const, text: c }))
        : [{ kind: 'paragraph' as const, text: s }]
    )
  }

  return chunkBySentence(text).map(text => ({ kind: 'paragraph' as const, text }))
}

/**
 * Parse a raw job description string into structured blocks for display.
 * Handles both well-structured text (with newlines/bullets, e.g. from the
 * improved scraper) and collapsed blobs (existing jobs where HTML structure
 * was lost at scrape time, or where section headers are glued into the
 * running prose with no whitespace structure at all).
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
