import { useCallback, useEffect, useState } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
  ExclamationCircleIcon,
  EyeIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarSolid } from '@heroicons/react/24/solid'
import { StarIcon as StarOutline } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { cvApi } from '../services/api'
import type { CV } from '../types'

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
      <div className="h-9 w-9 bg-gray-100 rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 bg-gray-100 rounded w-2/5" />
        <div className="h-3 bg-gray-100 rounded w-1/4" />
      </div>
      <div className="h-3 bg-gray-100 rounded w-14 hidden sm:block" />
      <div className="h-3 bg-gray-100 rounded w-24 hidden md:block" />
      <div className="flex gap-1.5">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-8 w-8 bg-gray-100 rounded-lg" />
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
        <h1 className="text-2xl font-bold text-gray-900">My CVs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload and manage your CVs for AI-powered tailoring.
        </p>
      </div>

      {/* Upload card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Upload a CV</h2>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer select-none transition-colors ${
            isDragActive
              ? 'border-brand-400 bg-brand-50'
              : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
          } ${uploadPct !== null ? 'pointer-events-none opacity-60' : ''}`}
        >
          <input {...getInputProps()} />
          <ArrowUpTrayIcon className="mx-auto h-8 w-8 text-gray-400 mb-3" />
          {isDragActive ? (
            <p className="text-sm font-medium text-brand-600">Drop your file here…</p>
          ) : (
            <>
              <p className="text-sm font-medium text-gray-700">
                Drag & drop your CV here, or{' '}
                <span className="text-brand-600">click to browse</span>
              </p>
              <p className="mt-1 text-xs text-gray-400">PDF or DOCX · max 10 MB</p>
            </>
          )}
        </div>

        {/* Pending file row */}
        {pendingFile && uploadPct === null && (
          <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200">
            <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{pendingFile.name}</p>
              <p className="text-xs text-gray-400">{formatBytes(pendingFile.size)}</p>
            </div>
            <input
              value={pendingTitle}
              onChange={(e) => setPendingTitle(e.target.value)}
              placeholder="CV title"
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-44 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleUpload}
                className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
              >
                <ArrowUpTrayIcon className="h-3.5 w-3.5" />
                Upload
              </button>
              <button
                onClick={() => setPendingFile(null)}
                className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Upload progress */}
        {uploadPct !== null && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span className="truncate">Uploading {pendingFile?.name}</span>
              <span className="flex-shrink-0 ml-2">{uploadPct}%</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all duration-200"
                style={{ width: `${uploadPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* CV list */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">
            Your CVs{' '}
            {!loading && cvs.length > 0 && (
              <span className="font-normal text-gray-400">({cvs.length})</span>
            )}
          </h2>
        </div>

        {loading ? (
          <div className="divide-y divide-gray-100">
            {[...Array(3)].map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : cvs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
            <div className="h-12 w-12 bg-blue-50 rounded-xl flex items-center justify-center mb-3">
              <DocumentTextIcon className="h-6 w-6 text-blue-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-900">No CVs yet</h3>
            <p className="mt-1 text-sm text-gray-400">
              Upload your first CV above to get started.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {cvs.map((cv) => (
              <div
                key={cv.id}
                className="px-6 py-4 flex items-center gap-4 hover:bg-gray-50 transition-colors"
              >
                {/* Icon */}
                <div className="h-9 w-9 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <DocumentTextIcon className="h-5 w-5 text-blue-500" />
                </div>

                {/* Title + filename */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-gray-900 truncate">{cv.title}</p>
                    {cv.is_default && (
                      <span className="inline-flex items-center gap-0.5 text-xs bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded-full font-medium flex-shrink-0">
                        <StarSolid className="h-2.5 w-2.5" />
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 truncate">{cv.filename}</p>
                </div>

                {/* Size */}
                <span className="text-xs text-gray-400 flex-shrink-0 hidden sm:block w-16 text-right">
                  {formatBytes(cv.file_size)}
                </span>

                {/* Date */}
                <span className="text-xs text-gray-400 flex-shrink-0 hidden md:block w-28 text-right">
                  {formatDate(cv.created_at)}
                </span>

                {/* Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => cvApi.view(cv.id).catch(() => toast.error('Could not open CV'))}
                    className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                    title="View"
                  >
                    <EyeIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => cvApi.download(cv.id, cv.filename).catch(() => toast.error('Could not download CV'))}
                    className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                    title="Download"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleSetDefault(cv)}
                    disabled={cv.is_default}
                    className={`h-8 w-8 flex items-center justify-center rounded-lg transition-colors ${
                      cv.is_default
                        ? 'text-brand-500 cursor-default'
                        : 'text-gray-400 hover:text-brand-600 hover:bg-brand-50'
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
                    className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
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
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <ExclamationCircleIcon className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base font-semibold text-gray-900">
                  Delete CV
                </DialogTitle>
                <p className="mt-1 text-sm text-gray-500">
                  Are you sure you want to delete{' '}
                  <strong>"{deleteTarget?.title}"</strong>? This cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
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
    </div>
  )
}
