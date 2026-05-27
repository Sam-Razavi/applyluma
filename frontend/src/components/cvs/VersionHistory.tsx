import { useEffect, useState } from 'react'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { cvApi } from '../../services/api'
import type { CV, CVVersionNode } from '../../types'
import VersionTreeNode from './VersionTreeNode'

interface Props {
  cv: CV | null
  open: boolean
  onClose: () => void
  onViewDiff: (node: CVVersionNode) => void
}

export default function VersionHistory({ cv, open, onClose, onViewDiff }: Props) {
  const [tree, setTree] = useState<CVVersionNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !cv) return

    let cancelled = false
    setLoading(true)
    setError(null)
    setTree(null)

    cvApi
      .getHistory(cv.id)
      .then((data) => {
        if (!cancelled) setTree(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load version history')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [cv, open])

  return (
    <Dialog open={open} onClose={onClose} className="relative z-40">
      <div className="fixed inset-0 bg-black/20" aria-hidden="true" />
      <div className="fixed inset-y-0 right-0 flex w-full justify-end sm:w-auto">
        <DialogPanel className="h-full w-full max-w-xl overflow-y-auto bg-white shadow-xl">
          <div className="sticky top-0 z-10 flex items-start justify-between border-b border-gray-100 bg-white px-6 py-5">
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold text-gray-900">
                Version History
              </DialogTitle>
              <p className="mt-1 truncate text-sm text-gray-500">{cv?.title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label="Close version history"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4 p-6">
            {loading && (
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
                Loading version tree...
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
                {error}
              </div>
            )}

            {tree && (
              <div className="space-y-2">
                <VersionTreeNode node={tree} onViewDiff={onViewDiff} />
              </div>
            )}

            {!loading && !error && !tree && (
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
                No version history found.
              </div>
            )}

            <p className="text-xs text-gray-400">
              Tailored versions can be opened to review section-level changes.
            </p>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  )
}
