import { useState } from 'react'
import { TrashIcon } from '@heroicons/react/24/outline'
import type { CoverLetterJob } from '../../../types/coverLetter'

interface HistorySectionProps {
  history: CoverLetterJob[]
  loading: boolean
  onDelete: (id: string) => void
}

export function HistorySection({ history, loading, onDelete }: HistorySectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-2xl border border-line bg-surface">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-6 py-4 text-sm font-semibold text-fg-muted"
      >
        <span>Cover letter history ({history.length})</span>
        <span className="text-fg-subtle">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="divide-y divide-line border-t border-line">
          {loading ? (
            <div className="px-6 py-4 text-sm text-fg-subtle">Loading…</div>
          ) : history.length === 0 ? (
            <div className="px-6 py-4 text-sm text-fg-subtle">No cover letters yet.</div>
          ) : (
            history.map((job) => (
              <div key={job.id} className="flex items-center justify-between gap-4 px-6 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-fg">
                    {job.title || 'Untitled cover letter'}
                  </p>
                  <p className="mt-0.5 text-xs text-fg-subtle">
                    {job.tone} · {job.status} · {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onDelete(job.id)}
                  className="shrink-0 rounded-lg p-1.5 text-chip-danger-fg hover:bg-chip-danger"
                  title="Delete"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
