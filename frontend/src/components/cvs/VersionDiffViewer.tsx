import { useEffect, useState } from 'react'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { cvApi } from '../../services/api'
import type { CVDiffResponse } from '../../types'

interface Props {
  cvId: string | null
  title: string | null
  open: boolean
  onClose: () => void
}

export default function VersionDiffViewer({ cvId, title, open, onClose }: Props) {
  const [diff, setDiff] = useState<CVDiffResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !cvId) return

    let cancelled = false
    setLoading(true)
    setError(null)
    setDiff(null)

    cvApi
      .getDiff(cvId)
      .then((data) => {
        if (!cancelled) setDiff(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load section diff')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [cvId, open])

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-4">
        <DialogPanel className="flex max-h-[90vh] w-full max-w-[64rem] flex-col overflow-hidden rounded-2xl bg-[#0C1218] shadow-2xl">
          <div className="flex items-start justify-between border-b border-white/10 px-6 py-4">
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold text-white/90">
                Section Diff
              </DialogTitle>
              <p className="mt-1 truncate text-sm text-white/30">{title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-white/30 transition hover:bg-white/[0.06] hover:text-white/55"
              aria-label="Close section diff"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="overflow-y-auto p-6">
            {loading && (
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/30">
                Loading section diff...
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-[rgba(229,72,77,0.18)] bg-[rgba(229,72,77,0.12)] p-4 text-sm text-red-300">
                {error}
              </div>
            )}

            {diff && diff.sections.length === 0 && (
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/30">
                No section changes were returned for this CV.
              </div>
            )}

            {diff && diff.sections.length > 0 && (
              <div className="space-y-4">
                {diff.sections.map((section) => {
                  const changed = section.changes > 0
                  return (
                    <section
                      key={section.name}
                      className={`overflow-hidden rounded-xl border ${
                        changed ? 'border-[rgba(245,158,11,0.20)] bg-[rgba(245,158,11,0.14)]/40' : 'border-white/10 bg-white/[0.04]'
                      }`}
                    >
                      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                        <h3 className="text-sm font-semibold text-white/90">{section.name}</h3>
                        {changed && (
                          <span className="rounded-full bg-[rgba(245,158,11,0.14)] px-2 py-0.5 text-xs font-semibold text-amber-300">
                            {section.changes} changes
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-1 divide-y divide-white/10 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
                        <div className="p-4">
                          <p className="mb-2 text-xs font-medium uppercase text-white/30">
                            Original
                          </p>
                          <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-white/55">
                            {section.original}
                          </pre>
                        </div>
                        <div className="p-4">
                          <p className="mb-2 text-xs font-medium uppercase text-primary-400">
                            Tailored
                          </p>
                          <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-white/90">
                            {section.tailored}
                          </pre>
                        </div>
                      </div>
                    </section>
                  )
                })}
              </div>
            )}
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  )
}
