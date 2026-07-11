import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { ArrowPathIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { CvTemplateId } from '../../types/tailor'
import { TEMPLATE_OPTIONS } from './templateOptions'

interface Props {
  open: boolean
  templateId: CvTemplateId
  onClose: () => void
  onTemplateChange: (value: CvTemplateId) => void
  /** Fetches the server-rendered CV HTML for a given template. */
  fetchHtml: (templateId: CvTemplateId) => Promise<string>
}

export function TemplatePreviewModal({
  open,
  templateId,
  onClose,
  onTemplateChange,
  fetchHtml,
}: Props) {
  const [html, setHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  // Guards against a slow response for one template overwriting a newer one.
  const requestSeq = useRef(0)

  const load = useCallback(
    (id: CvTemplateId) => {
      const seq = ++requestSeq.current
      setLoading(true)
      setError(false)
      fetchHtml(id)
        .then((result) => {
          if (requestSeq.current !== seq) return
          setHtml(result)
          setLoading(false)
        })
        .catch(() => {
          if (requestSeq.current !== seq) return
          setError(true)
          setLoading(false)
        })
    },
    [fetchHtml],
  )

  useEffect(() => {
    if (open) load(templateId)
  }, [open, templateId, load])

  return (
    <Dialog open={open} onClose={onClose} className="relative z-modal">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="flex max-h-[92vh] w-full max-w-[880px] flex-col rounded-2xl border border-line bg-raised p-4 shadow-2xl sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <DialogTitle className="text-base font-semibold text-fg">CV preview</DialogTitle>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close preview"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-strong text-fg-muted transition hover:text-fg"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {TEMPLATE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={templateId === option.value}
                onClick={() => onTemplateChange(option.value)}
                className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  templateId === option.value
                    ? 'border-brand-500 bg-primary-900/20 text-fg'
                    : 'border-line text-fg-muted hover:border-line-strong hover:text-fg'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="mt-3 min-h-0 flex-1">
            {error ? (
              <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-lg border border-line bg-surface text-sm text-fg-subtle">
                <p>Could not load the preview.</p>
                <button
                  type="button"
                  onClick={() => load(templateId)}
                  className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 font-semibold text-fg-muted transition hover:bg-surface-strong hover:text-fg"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  Try again
                </button>
              </div>
            ) : loading ? (
              <div
                role="status"
                aria-label="Loading preview"
                className="flex h-64 items-center justify-center rounded-lg border border-line bg-surface"
              >
                <ArrowPathIcon className="h-6 w-6 animate-spin text-fg-subtle" />
              </div>
            ) : (
              <iframe
                sandbox=""
                srcDoc={html}
                title="CV preview"
                className="h-[65vh] w-full rounded-lg border border-line bg-white"
              />
            )}
          </div>

          <p className="mt-2 text-xs text-fg-subtle">
            The saved PDF uses the same layout; exact page breaks can differ slightly.
          </p>
        </DialogPanel>
      </div>
    </Dialog>
  )
}
