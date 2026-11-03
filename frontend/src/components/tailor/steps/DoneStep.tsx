import { useState } from 'react'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  BriefcaseIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { cvApi } from '../../../services/api'

interface DoneStepProps {
  wantCv: boolean
  wantCover: boolean
  savedCvId: string | null
  savedCvTitle: string
  coverText: string
  coverTitle: string
  coverSaved: boolean
  jobUrl: string | null
  applicationStatus: string | null
  addingApplication: boolean
  onAddToApplications: () => void
  onCopy: () => void
  onDownloadCoverPdf: () => void
  onDownloadTxt: () => void
  onReset: () => void
}

export function DoneStep({
  wantCv,
  wantCover,
  savedCvId,
  savedCvTitle,
  coverText,
  coverTitle,
  coverSaved,
  jobUrl,
  applicationStatus,
  addingApplication,
  onAddToApplications,
  onCopy,
  onDownloadCoverPdf,
  onDownloadTxt,
  onReset,
}: DoneStepProps) {
  const [downloadingCv, setDownloadingCv] = useState(false)

  async function handleDownloadCv() {
    if (!savedCvId) return
    setDownloadingCv(true)
    try {
      await cvApi.download(savedCvId, savedCvTitle ? `${savedCvTitle}.pdf` : 'tailored-cv.pdf')
    } catch {
      toast.error('Could not download the tailored CV')
    } finally {
      setDownloadingCv(false)
    }
  }

  return (
    <div className="space-y-6 rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-chip-success">
          <CheckCircleIcon className="h-6 w-6 text-chip-success-fg" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-fg">
            {wantCv && wantCover ? 'CV and cover letter saved' : wantCv ? 'Tailored CV saved' : 'Cover letter saved'}
          </h2>
          <p className="mt-0.5 text-sm text-fg-subtle">
            Your original CV stays unchanged. Download or copy your documents below.
          </p>
        </div>
      </div>

      {wantCv && savedCvId && (
        <div className="space-y-2 rounded-xl border border-line p-4">
          <p className="text-sm font-semibold text-fg">Tailored CV</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleDownloadCv}
              disabled={downloadingCv}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {downloadingCv ? (
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowDownTrayIcon className="h-4 w-4" />
              )}
              Download PDF
            </button>
            <Link
              to="/cvs"
              className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
            >
              View in My CVs
            </Link>
          </div>
        </div>
      )}

      {wantCover && coverSaved && (
        <div className="space-y-3 rounded-xl border border-line p-4">
          <p className="text-sm font-semibold text-fg">Cover letter{coverTitle ? ` — ${coverTitle}` : ''}</p>
          <pre className="max-h-[320px] overflow-y-auto whitespace-pre-wrap rounded-lg bg-surface p-3 text-sm leading-relaxed text-fg-muted">
            {coverText}
          </pre>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onDownloadCoverPdf}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Download PDF
            </button>
            <button
              type="button"
              onClick={onCopy}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-strong"
            >
              <ClipboardDocumentIcon className="h-4 w-4" />
              Copy text
            </button>
            <button
              type="button"
              onClick={onDownloadTxt}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-strong"
            >
              <DocumentTextIcon className="h-4 w-4" />
              Download .txt
            </button>
          </div>
        </div>
      )}

      {/* Apply nudge — close the loop from tailoring to applying. */}
      <div className="space-y-3 rounded-xl border border-primary-600/30 bg-primary-900/20 p-4">
        <p className="text-sm font-semibold text-fg">Ready to apply?</p>
        <div className="flex flex-wrap items-center gap-2">
          {jobUrl && (
            <a
              href={jobUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              <ArrowTopRightOnSquareIcon className="h-4 w-4" />
              Apply now
            </a>
          )}
          {applicationStatus ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-lg bg-chip-success px-3 py-1.5 text-sm font-medium text-chip-success-fg">
                <BriefcaseIcon className="h-4 w-4" />
                {applicationStatus.replace('_', ' ')}
              </span>
              <Link
                to="/applications"
                className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
              >
                View in Applications
              </Link>
            </div>
          ) : (
            <button
              type="button"
              onClick={onAddToApplications}
              disabled={addingApplication}
              className="inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50"
            >
              <BriefcaseIcon className="h-4 w-4" />
              {addingApplication ? 'Adding…' : 'Add to Applications'}
            </button>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="inline-flex items-center gap-2 rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong"
      >
        <SparklesIcon className="h-4 w-4" />
        Start another
      </button>
    </div>
  )
}
