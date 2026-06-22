import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { AnimatePresence, motion } from 'framer-motion'
import type { TailorSection } from '../../types/tailor'

interface Props {
  section: TailorSection
  accepted: boolean
  onToggle: () => void
}

export function SectionDiff({ section, accepted, onToggle }: Props) {
  return (
    <div
      className={`overflow-hidden rounded-xl border-2 transition-colors ${
        accepted ? 'border-primary-600/30 bg-brand-50/30' : 'border-line bg-surface/50'
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h3 className="text-sm font-semibold text-fg">{section.section_name}</h3>
        <button
          type="button"
          onClick={onToggle}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            accepted
              ? 'bg-primary-900/30 text-accent-text hover:bg-brand-200'
              : 'bg-surface text-fg-subtle hover:bg-surface-strong'
          }`}
        >
          {accepted ? <CheckIcon className="h-3.5 w-3.5" /> : <XMarkIcon className="h-3.5 w-3.5" />}
          {accepted ? 'Accepted' : 'Rejected'}
        </button>
      </div>

      <AnimatePresence initial={false}>
        <motion.div
          key="diff-content"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          style={{ overflow: 'hidden' }}
        >
          <div className="grid grid-cols-1 divide-y divide-line md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-fg-subtle">Original</p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-fg-muted">
                {section.original}
              </pre>
            </div>
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-accent-text">
                Tailored
              </p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-fg">
                {section.tailored}
              </pre>
            </div>
          </div>

          {section.changes.length > 0 && (
            <div className="border-t border-line bg-chip-warn/50 px-4 py-3">
              <p className="mb-1 text-xs font-medium text-fg-subtle">Changes made</p>
              <ul className="space-y-0.5">
                {section.changes.map((change, index) => (
                  <li key={`${section.section_id}-${index}`} className="text-xs text-fg-muted">
                    - {change}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
