import type { CvTemplateId } from '../../types/tailor'

export const TEMPLATE_OPTIONS: { value: CvTemplateId; label: string; description: string }[] = [
  {
    value: 'nordic',
    label: 'Nordic',
    description: 'Navy header with teal accents and a skills panel. Modern Scandinavian look.',
  },
  {
    value: 'classic',
    label: 'Classic',
    description: 'Clean black-and-white layout. Maximum ATS compatibility.',
  },
  {
    value: 'modern',
    label: 'Modern',
    description: 'Violet accents with skill chips. Bold look for tech and startup roles.',
  },
  {
    value: 'executive',
    label: 'Executive',
    description: 'Centered serif layout with refined rules. Formal, senior-level tone.',
  },
  {
    value: 'atlas',
    label: 'Atlas',
    description: 'Two-column layout with an emerald sidebar for skills and education. Best for human readers; some ATS systems parse two columns less reliably.',
  },
  {
    value: 'compact',
    label: 'Compact',
    description: 'Dense single-column layout with tight spacing. Fits more experience into two pages.',
  },
]
