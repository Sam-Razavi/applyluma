import { useState } from 'react'
import {
  CheckIcon,
  XMarkIcon,
  PencilIcon,
  ChevronUpIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import { AnimatePresence, motion } from 'framer-motion'
import type { TailorSection } from '../../types/tailor'

interface Props {
  section: TailorSection
  accepted: boolean
  onToggle: () => void
  editedText?: string
  onEdit: (text: string) => void
  onMoveUp?: () => void
  onMoveDown?: () => void
  isFirst?: boolean
  isLast?: boolean
}

export function SectionDiff({
  section,
  accepted,
  onToggle,
  editedText,
  onEdit,
  onMoveUp,
  onMoveDown,
  isFirst = false,
  isLast = false,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const isEdited = editedText !== undefined && editedText !== section.tailored
  const displayText = editedText ?? section.tailored

  function startEditing() {
    setDraft(displayText)
    setEditing(true)
  }

  function confirmEdit() {
    onEdit(draft)
    setEditing(false)
  }

  function cancelEdit() {
    setEditing(false)
  }

  return (
    <div
      className={`overflow-hidden rounded-xl border-2 transition-colors ${
        accepted ? 'border-primary-600/30 bg-brand-50/30' : 'border-line bg-surface/50'
      }`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-fg">{section.section_name}</h3>
          {isEdited && (
            <span className="rounded-full bg-chip-info px-2 py-0.5 text-[10px] font-medium text-chip-info-fg">
              edited
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {onMoveUp && (
            <button
              type="button"
              onClick={onMoveUp}
              disabled={isFirst}
              title="Move up"
              className="rounded p-1 text-fg-subtle transition-colors hover:bg-surface-strong disabled:opacity-30"
            >
              <ChevronUpIcon className="h-4 w-4" />
            </button>
          )}
          {onMoveDown && (
            <button
              type="button"
              onClick={onMoveDown}
              disabled={isLast}
              title="Move down"
              className="rounded p-1 text-fg-subtle transition-colors hover:bg-surface-strong disabled:opacity-30"
            >
              <ChevronDownIcon className="h-4 w-4" />
            </button>
          )}
          <button
            type="button"
            onClick={startEditing}
            title="Edit tailored text"
            className="rounded p-1 text-fg-subtle transition-colors hover:bg-surface-strong"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
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
                Tailored {isEdited && '(edited)'}
              </p>
              {editing ? (
                <div className="space-y-2">
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={10}
                    className="w-full rounded-lg border border-line bg-surface px-3 py-2 font-sans text-xs leading-relaxed text-fg focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="rounded-lg px-3 py-1.5 text-xs font-medium text-fg-muted hover:bg-surface-strong"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={confirmEdit}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
                    >
                      Save edit
                    </button>
                  </div>
                </div>
              ) : (
                <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-fg">
                  {displayText}
                </pre>
              )}
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
