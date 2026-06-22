import { useCallback, useEffect, useState } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { motion } from 'framer-motion'
import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationCircleIcon,
  EyeIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarSolid } from '@heroicons/react/24/solid'
import { StarIcon as StarOutline } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import VersionDiffViewer from '../components/cvs/VersionDiffViewer'
import VersionHistory from '../components/cvs/VersionHistory'
import { cvApi } from '../services/api'
import type { CV, CVVersionNode } from '../types'

const MAX_SIZE = 10 * 1024 * 1024
const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

function formatBytes(n: number | null) {
  if (!n) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1_048_576) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1_048_576).toFixed(1)} MB`
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function SkeletonRow() {
  return (
    <div className="px-6 py-4 flex items-center gap-4 animate-pulse">
      <div className="h-9 w-9 bg-surface rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 bg-surface rounded w-2/5" />
        <div className="h-3 bg-surface rounded w-1/4" />
      </div>
      <div className="h-3 bg-surface rounded w-14 hidden sm:block" />
      <div className="h-3 bg-surface rounded w-24 hidden md:block" />
      <div className="flex gap-1.5">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-8 w-8 bg-surface rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export default function CVs() {
  const [cvs, setCvs] = useState<CV[]>([])
  const [loading, setLoading] = useState(true)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [pendingTitle, setPendingTitle] = useState('')
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CV | null>(null)
  const [historyTarget, setHistoryTarget] = useState<CV | null>(null)
  const [diffTarget, setDiffTarget] = useState<CVVersionNode | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    cvApi
      .list()
      .then(setCvs)
      .catch(() => toast.error('Failed to load CVs'))
      .finally(() => setLoading(false))
  }, [])

  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    if (rejected.length > 0) {
      const code = rejected[0].errors[0]?.code
      if (code === 'file-too-large') toast.error('File is too large. Max 10 MB.')
      else if (code === 'file-invalid-type') toast.error('Only PDF and DOCX files are accepted.')
      else toast.error('File rejected.')
      return
    }
    const file = accepted[0]
    if (!file) return
    setPendingFile(file)
    setPendingTitle(file.name.replace(/\.[^.]+$/, ''))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    multiple: false,
    disabled: uploadPct !== null,
  })

  async function handleUpload() {
    if (!pendingFile) return
    setUploadPct(0)
    try {
      const cv = await cvApi.upload(pendingFile, pendingTitle || undefined, setUploadPct)
      setCvs((prev) => [cv, ...prev])
      toast.success('CV uploaded!')
      import('posthog-js').then(({ default: posthog }) => posthog.capture('cv_uploaded'))
      setPendingFile(null)
      setPendingTitle('')
    } catch {
      toast.error('Upload failed. Please try again.')
    } finally {
      setUploadPct(null)
    }
  }

  async function handleSetDefault(cv: CV) {
    try {
      const updated = await cvApi.setDefault(cv.id)
      setCvs((prev) => prev.map((c) => ({ ...c, is_default: c.id === updated.id })))
      toast.success(`"${cv.title}" set as default`)
    } catch {
      toast.error('Could not set default CV')
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await cvApi.remove(deleteTarget.id)
      setCvs((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      toast.success('CV deleted')
      setDeleteTarget(null)
    } catch {
      toast.error('Could not delete CV')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-fg">My CVs</h1>
        <p className="mt-1 text-sm text-fg-subtle">
          Upload and manage your CVs for AI-powered tailoring.
        </p>
      </div>

      {/* Upload card */}
      <div className="bg-surface rounded-2xl border border-line p-6 space-y-4">
        <h2 className="text-sm font-semibold text-fg-muted">Upload a CV</h2>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer select-none transition-colors sm:p-10 ${
            isDragActive
              ? 'border-primary-500/50 bg-primary-900/20'
              : 'border-line-strong hover:border-brand-400 hover:bg-surface-strong'
          } ${uploadPct !== null ? 'pointer-events-none opacity-60' : ''}`}
        >
          <input {...getInputProps()} />
          <ArrowUpTrayIcon className="mx-auto h-8 w-8 text-fg-subtle mb-3" />
          {isDragActive ? (
            <p className="text-sm font-medium text-accent-text">Drop your file here…</p>
          ) : (
            <>
              <p className="text-sm font-medium text-fg-muted">
                Drag & drop your CV here, or{' '}
                <span className="text-accent-text">click to browse</span>
              </p>
              <p className="mt-1 text-xs text-fg-subtle">PDF or DOCX · max 10 MB</p>
            </>
          )}
        </div>

        {/* Pending file row */}
        {pendingFile && uploadPct === null && (
          <div className="flex flex-wrap items-center gap-3 p-4 bg-surface rounded-xl border border-line">
            <DocumentTextIcon className="h-5 w-5 text-fg-subtle flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-fg-muted truncate">{pendingFile.name}</p>
              <p className="text-xs text-fg-subtle">{formatBytes(pendingFile.size)}</p>
            </div>
            <input
              value={pendingTitle}
              onChange={(e) => setPendingTitle(e.target.value)}
              placeholder="CV title"
              className="min-h-11 w-full rounded-lg border border-line px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 sm:w-44"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleUpload}
                className="inline-flex min-h-11 items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
              >
                <ArrowUpTrayIcon className="h-3.5 w-3.5" />
                Upload
              </button>
              <button
                onClick={() => setPendingFile(null)}
                className="min-h-11 rounded-lg px-3 py-2.5 text-sm text-fg-subtle transition-colors hover:bg-surface-strong hover:text-fg-muted"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Upload progress */}
        {uploadPct !== null && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-fg-subtle">
              <span className="truncate">Uploading {pendingFile?.name}</span>
              <span className="flex-shrink-0 ml-2">{uploadPct}%</span>
            </div>
            <div className="h-2 bg-track rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-brand-500"
                initial={{ width: 0 }}
                animate={{ width: `${uploadPct}%` }}
                transition={{ ease: 'linear', duration: 0.1 }}
              />
            </div>
          </div>
        )}
      </div>

      {/* CV list */}
      <div className="bg-surface rounded-2xl border border-line overflow-hidden">
        <div className="px-6 py-4 border-b border-line">
          <h2 className="text-sm font-semibold text-fg-muted">
            Your CVs{' '}
            {!loading && cvs.length > 0 && (
              <span className="font-normal text-fg-subtle">({cvs.length})</span>
            )}
          </h2>
        </div>

        {loading ? (
          <div className="divide-y divide-line">
            {[...Array(3)].map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : cvs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <div className="h-12 w-12 bg-chip-accent rounded-xl flex items-center justify-center mb-3">
              <DocumentTextIcon className="h-6 w-6 text-blue-400" />
            </div>
            <h3 className="text-sm font-medium text-fg">No CVs yet</h3>
            <p className="mt-1 text-sm text-fg-subtle">
              Upload your first CV above to get started.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {cvs.map((cv) => (
              <div
                key={cv.id}
                className="flex items-start gap-4 px-6 py-4 transition-colors hover:bg-surface-strong sm:items-center"
              >
                {/* Icon */}
                <div className="h-9 w-9 bg-chip-accent rounded-lg flex items-center justify-center flex-shrink-0">
                  <DocumentTextIcon className="h-5 w-5 text-blue-500" />
                </div>

                {/* Title + filename */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-fg truncate">{cv.title}</p>
                    {cv.is_default && (
                      <span className="inline-flex items-center gap-0.5 text-xs bg-primary-900/30 text-accent-text px-1.5 py-0.5 rounded-full font-medium flex-shrink-0">
                        <StarSolid className="h-2.5 w-2.5" />
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-fg-subtle truncate">{cv.filename}</p>
                </div>

                {/* Size */}
                <span className="text-xs text-fg-subtle flex-shrink-0 hidden sm:block w-16 text-right">
                  {formatBytes(cv.file_size)}
                </span>

                {/* Date */}
                <span className="text-xs text-fg-subtle flex-shrink-0 hidden md:block w-28 text-right">
                  {formatDate(cv.created_at)}
                </span>

                {/* Actions */}
                <div className="flex flex-shrink-0 flex-col items-center gap-1 sm:flex-row">
                  <button
                    onClick={() => cvApi.view(cv.id).catch(() => toast.error('Could not open CV'))}
                    className="flex h-10 w-10 items-center justify-center rounded-lg text-fg-subtle transition-colors hover:bg-surface-strong hover:text-fg-muted"
                    title="View"
                  >
                    <EyeIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => cvApi.download(cv.id, cv.filename).catch(() => toast.error('Could not download CV'))}
                    className="flex h-10 w-10 items-center justify-center rounded-lg text-fg-subtle transition-colors hover:bg-surface-strong hover:text-fg-muted"
                    title="Download"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4" />
                  </button>
                  {cv.is_tailored && (
                    <button
                      onClick={() => setHistoryTarget(cv)}
                      className="inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-fg-subtle transition-colors hover:bg-primary-900/20 hover:text-accent-text"
                      title="Version History"
                    >
                      <ClockIcon className="h-4 w-4" />
                      <span className="hidden lg:inline">History</span>
                    </button>
                  )}
                  <button
                    onClick={() => handleSetDefault(cv)}
                    disabled={cv.is_default}
                    className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                      cv.is_default
                        ? 'text-accent-text cursor-default'
                        : 'text-fg-subtle hover:text-accent-text hover:bg-primary-900/20'
                    }`}
                    title={cv.is_default ? 'Default CV' : 'Set as default'}
                  >
                    {cv.is_default ? (
                      <StarSolid className="h-4 w-4" />
                    ) : (
                      <StarOutline className="h-4 w-4" />
                    )}
                  </button>
                  <button
                    onClick={() => setDeleteTarget(cv)}
                    className="flex h-10 w-10 items-center justify-center rounded-lg text-fg-subtle transition-colors hover:bg-chip-danger text-chip-danger-fg"
                    title="Delete"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => !deleting && setDeleteTarget(null)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-surface rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-chip-danger rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-chip-danger-fg" />
              </div>
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base font-semibold text-fg">
                  Delete CV
                </DialogTitle>
                <p className="mt-1 text-sm text-fg-subtle">
                  Are you sure you want to delete{' '}
                  <strong>"{deleteTarget?.title}"</strong>? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-fg-muted bg-surface hover:bg-surface-strong rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>

      <VersionHistory
        cv={historyTarget}
        open={!!historyTarget}
        onClose={() => setHistoryTarget(null)}
        onViewDiff={setDiffTarget}
      />

      <VersionDiffViewer
        cvId={diffTarget?.id ?? null}
        title={diffTarget?.title ?? null}
        open={!!diffTarget}
        onClose={() => setDiffTarget(null)}
      />
    </div>
  )
}
