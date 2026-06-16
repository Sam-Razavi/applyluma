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
        accepted ? 'border-primary-600/30 bg-brand-50/30' : 'border-white/10 bg-white/[0.03]/50'
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
        <h3 className="text-sm font-semibold text-white/90">{section.section_name}</h3>
        <button
          type="button"
          onClick={onToggle}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            accepted
              ? 'bg-primary-900/30 text-primary-400 hover:bg-brand-200'
              : 'bg-white/[0.04] text-white/30 hover:bg-white/[0.08]'
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
          <div className="grid grid-cols-1 divide-y divide-white/10 md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-white/30">Original</p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-white/55">
                {section.original}
              </pre>
            </div>
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-primary-400">
                Tailored
              </p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-white/90">
                {section.tailored}
              </pre>
            </div>
          </div>

          {section.changes.length > 0 && (
            <div className="border-t border-white/10 bg-[rgba(245,158,11,0.14)]/50 px-4 py-3">
              <p className="mb-1 text-xs font-medium text-white/30">Changes made</p>
              <ul className="space-y-0.5">
                {section.changes.map((change, index) => (
                  <li key={`${section.section_id}-${index}`} className="text-xs text-white/55">
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
