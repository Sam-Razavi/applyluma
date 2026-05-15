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
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
          <div className="flex items-start justify-between border-b border-gray-100 px-6 py-4">
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold text-gray-900">
                Section Diff
              </DialogTitle>
              <p className="mt-1 truncate text-sm text-gray-500">{title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label="Close section diff"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="overflow-y-auto p-6">
            {loading && (
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
                Loading section diff...
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
                {error}
              </div>
            )}

            {diff && diff.sections.length === 0 && (
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
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
                        changed ? 'border-yellow-200 bg-yellow-50/40' : 'border-gray-200 bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
                        <h3 className="text-sm font-semibold text-gray-900">{section.name}</h3>
                        {changed && (
                          <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-semibold text-yellow-800">
                            {section.changes} changes
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-1 divide-y divide-gray-100 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
                        <div className="p-4">
                          <p className="mb-2 text-xs font-medium uppercase text-gray-400">
                            Original
                          </p>
                          <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-gray-600">
                            {section.original}
                          </pre>
                        </div>
                        <div className="p-4">
                          <p className="mb-2 text-xs font-medium uppercase text-brand-500">
                            Tailored
                          </p>
                          <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-gray-900">
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
