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
        accepted ? 'border-brand-200 bg-brand-50/30' : 'border-gray-200 bg-gray-50/50'
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800">{section.section_name}</h3>
        <button
          type="button"
          onClick={onToggle}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            accepted
              ? 'bg-brand-100 text-brand-700 hover:bg-brand-200'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
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
          <div className="grid grid-cols-1 divide-y divide-gray-100 md:grid-cols-2 md:divide-x md:divide-y-0">
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">Original</p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-gray-600">
                {section.original}
              </pre>
            </div>
            <div className="p-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-brand-500">
                Tailored
              </p>
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-gray-900">
                {section.tailored}
              </pre>
            </div>
          </div>

          {section.changes.length > 0 && (
            <div className="border-t border-gray-100 bg-amber-50/50 px-4 py-3">
              <p className="mb-1 text-xs font-medium text-gray-500">Changes made</p>
              <ul className="space-y-0.5">
                {section.changes.map((change, index) => (
                  <li key={`${section.section_id}-${index}`} className="text-xs text-gray-600">
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
