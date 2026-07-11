import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'

interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  loading?: boolean
  /** When set, the confirm button stays disabled until the user types this exact text. */
  requireText?: string
  onCancel: () => void
  onConfirm: () => void
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  loading = false,
  requireText,
  onCancel,
  onConfirm,
}: Props) {
  const [typed, setTyped] = useState('')
  const confirmDisabled = loading || (requireText !== undefined && typed !== requireText)

  function handleCancel() {
    setTyped('')
    onCancel()
  }

  return (
    <Dialog open={open} onClose={() => !loading && handleCancel()} className="relative z-modal-nested">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-sm rounded-2xl border border-line bg-raised p-6 shadow-2xl">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-chip-danger">
              <ExclamationTriangleIcon className="h-5 w-5 text-chip-danger-fg" />
            </div>
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold text-fg">{title}</DialogTitle>
              <p className="mt-2 text-sm leading-6 text-fg-subtle">{message}</p>
            </div>
          </div>

          {requireText !== undefined && (
            <div className="mt-4">
              <label className="text-xs font-medium text-fg-subtle">
                Type <span className="font-semibold text-fg">{requireText}</span> to confirm
              </label>
              <input
                type="text"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                disabled={loading}
                className="mt-1 w-full rounded-lg border border-line-strong px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                autoFocus
              />
            </div>
          )}

          <div className="mt-6 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              disabled={loading}
              className="rounded-lg border border-line px-4 py-2 text-sm font-semibold text-fg-muted transition hover:bg-surface-strong hover:text-fg disabled:opacity-50"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={confirmDisabled}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
            >
              {loading ? 'Deleting...' : confirmLabel}
            </button>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  )
}
