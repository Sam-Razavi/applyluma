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
      <div className="fixed inset-0 bg-black/60" aria-hidden="true" />
      <div className="fixed inset-y-0 right-0 flex w-full justify-end sm:w-auto">
        <DialogPanel className="h-full w-full max-w-xl overflow-y-auto bg-raised shadow-2xl">
          <div className="sticky top-0 z-10 flex items-start justify-between border-b border-line bg-raised px-6 py-5">
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold text-fg">
                Version History
              </DialogTitle>
              <p className="mt-1 truncate text-sm text-fg-subtle">{cv?.title}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-fg-subtle transition hover:bg-surface-strong hover:text-fg-muted"
              aria-label="Close version history"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4 p-6">
            {loading && (
              <div className="rounded-xl border border-line bg-surface p-4 text-sm text-fg-subtle">
                Loading version tree...
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-chip-danger bg-chip-danger p-4 text-sm text-chip-danger-fg">
                {error}
              </div>
            )}

            {tree && (
              <div className="space-y-2">
                <VersionTreeNode node={tree} onViewDiff={onViewDiff} />
              </div>
            )}

            {!loading && !error && !tree && (
              <div className="rounded-xl border border-line bg-surface p-4 text-sm text-fg-subtle">
                No version history found.
              </div>
            )}

            <p className="text-xs text-fg-subtle">
              Tailored versions can be opened to review section-level changes.
            </p>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  )
}
