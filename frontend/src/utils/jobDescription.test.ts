import { describe, it, expect } from 'vitest'
import { parseJobDescription } from './jobDescription'

describe('parseJobDescription', () => {
  describe('empty / trivial inputs', () => {
    it('returns [] for empty string', () => {
      expect(parseJobDescription('')).toEqual([])
    })

    it('returns [] for whitespace-only string', () => {
      expect(parseJobDescription('   \n  ')).toEqual([])
    })

    it('returns single paragraph for short description (< 100 chars)', () => {
      const result = parseJobDescription('Short job.')
      expect(result).toEqual([{ kind: 'paragraph', text: 'Short job.' }])
    })
  })

  describe('structured input (newlines + bullets)', () => {
    it('splits on double newlines into paragraphs', () => {
      const input = 'First paragraph.\n\nSecond paragraph.\n\nThird paragraph.'
      const result = parseJobDescription(input)
      expect(result).toHaveLength(3)
      expect(result[0]).toEqual({ kind: 'paragraph', text: 'First paragraph.' })
      expect(result[1]).toEqual({ kind: 'paragraph', text: 'Second paragraph.' })
      expect(result[2]).toEqual({ kind: 'paragraph', text: 'Third paragraph.' })
    })

    it('classifies bullet lines (•) as a bullet block', () => {
      const input = '• Python proficiency\n• 5+ years experience\n• Team player'
      const result = parseJobDescription(input)
      expect(result).toHaveLength(1)
      expect(result[0]).toEqual({
        kind: 'bullet',
        items: ['Python proficiency', '5+ years experience', 'Team player'],
      })
    })

    it('classifies dash-prefixed lines as a bullet block', () => {
      const input = '- Python proficiency\n- 5+ years experience'
      const result = parseJobDescription(input)
      expect(result[0].kind).toBe('bullet')
      if (result[0].kind === 'bullet') {
        expect(result[0].items).toContain('Python proficiency')
      }
    })

    it('classifies numbered lines as a numbered block', () => {
      const input = '1. Submit your CV\n2. Complete assessment\n3. Interview'
      const result = parseJobDescription(input)
      expect(result).toHaveLength(1)
      expect(result[0]).toEqual({
        kind: 'numbered',
        items: ['Submit your CV', 'Complete assessment', 'Interview'],
      })
    })

    it('classifies short single line before bullet chunk as heading', () => {
      const input = 'Requirements\n\n• Python\n• SQL'
      const result = parseJobDescription(input)
      expect(result[0]).toEqual({ kind: 'heading', text: 'Requirements' })
      expect(result[1]).toEqual({ kind: 'bullet', items: ['Python', 'SQL'] })
    })

    it('handles mixed blocks: heading + paragraph + bullet', () => {
      const input =
        'About the role\n\nWe are looking for a talented engineer.\n\n• Python\n• TypeScript'
      const result = parseJobDescription(input)
      expect(result[0].kind).toBe('heading')
      expect(result[1].kind).toBe('paragraph')
      expect(result[2].kind).toBe('bullet')
    })
  })

  describe('collapsed blob heuristic splitting', () => {
    it('splits at known section keyword boundary', () => {
      const input =
        'We are a fast-growing startup. Responsibilities: Lead the engineering team. Requirements: 5+ years of experience. Benefits: Competitive salary and equity.'
      const result = parseJobDescription(input)
      expect(result.length).toBeGreaterThanOrEqual(2)
      expect(result.every(b => b.kind === 'paragraph')).toBe(true)
    })

    it('splits at "Requirements" keyword', () => {
      const input =
        'Join our team and make an impact. Requirements: You have Python experience and a passion for building products.'
      const result = parseJobDescription(input)
      expect(result.length).toBeGreaterThanOrEqual(2)
      const texts = result.map(b => (b.kind === 'paragraph' ? b.text : ''))
      expect(texts.some(t => t.startsWith('Requirements:'))).toBe(true)
    })

    it('splits long blob without keywords at sentence boundaries', () => {
      const longSentence = (n: number) =>
        `This is sentence number ${n} and it is a complete thought with some length.`
      const blob = Array.from({ length: 10 }, (_, i) => longSentence(i + 1)).join(' ')
      const result = parseJobDescription(blob)
      expect(result.length).toBeGreaterThan(1)
      expect(result.every(b => b.kind === 'paragraph')).toBe(true)
    })
  })

  describe('residual HTML handling', () => {
    it('strips HTML tags from input', () => {
      const input = '<b>Senior Engineer</b> — Join our team. We build <i>great</i> products.'
      const result = parseJobDescription(input)
      expect(result.length).toBeGreaterThan(0)
      const allText = result.map(b => (b.kind === 'paragraph' ? b.text : '')).join(' ')
      expect(allText).not.toContain('<b>')
      expect(allText).not.toContain('<i>')
      expect(allText).toContain('Senior Engineer')
    })

    it('decodes &amp; entities', () => {
      const input = 'We build tools &amp; services for developers around the world every day.'
      const result = parseJobDescription(input)
      const allText = result.map(b => (b.kind === 'paragraph' ? b.text : '')).join(' ')
      expect(allText).toContain('tools & services')
    })

    it('decodes &lt; and &gt; entities', () => {
      const input =
        'Salary &lt;60k for juniors. Requirements: 2 years experience &amp; good communication skills.'
      const result = parseJobDescription(input)
      const allText = result.map(b => (b.kind === 'paragraph' ? b.text : '')).join(' ')
      expect(allText).toContain('<60k')
    })
  })

  describe('edge cases', () => {
    it('treats single newline in a long blob as collapsed (no structure detected)', () => {
      // Only 1 newline — hasStructure is false — should take blob path
      const blob =
        'We are hiring.\nJoin us and build great products with our talented engineering team today.'
      const result = parseJobDescription(blob)
      // blob path should be taken; result is paragraph blocks
      expect(result.every(b => b.kind === 'paragraph')).toBe(true)
    })

    it('does not emit empty paragraph blocks', () => {
      const input = 'Paragraph one.\n\n\n\n\nParagraph two.'
      const result = parseJobDescription(input)
      expect(result.every(b => b.kind !== 'paragraph' || b.text.length > 0)).toBe(true)
    })
  })
})
