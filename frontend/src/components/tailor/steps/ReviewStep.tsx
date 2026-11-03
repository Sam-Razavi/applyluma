import { useState } from 'react'
import { ArrowPathIcon, ClipboardDocumentIcon, EyeIcon } from '@heroicons/react/24/outline'
import { SectionDiff } from '../SectionDiff'
import { TailorSummary } from '../TailorSummary'
import { TemplatePicker } from '../TemplatePicker'
import { TemplatePreviewModal } from '../TemplatePreviewModal'
import type { CvTemplateId, TailorPreview } from '../../../types/tailor'

interface ReviewStepProps {
  wantCv: boolean
  wantCover: boolean
  preview: TailorPreview | null
  acceptedIds: Set<string>
  editedContent: Map<string, string>
  sectionOrder: string[]
  cvTitle: string
  templateId: CvTemplateId
  coverText: string
  coverTitle: string
  saving: boolean
  onToggle: (sectionId: string) => void
  onEditSection: (id: string, text: string) => void
  onMove: (id: string, direction: -1 | 1) => void
  onCvTitleChange: (value: string) => void
  onTemplateChange: (value: CvTemplateId) => void
  onFetchPreviewHtml: (templateId: CvTemplateId) => Promise<string>
  onCoverTextChange: (value: string) => void
  onCoverTitleChange: (value: string) => void
  onCopy: () => void
  onSave: () => void
  onBack: () => void
}

export function ReviewStep({
  wantCv,
  wantCover,
  preview,
  acceptedIds,
  editedContent,
  sectionOrder,
  cvTitle,
  templateId,
  coverText,
  coverTitle,
  saving,
  onToggle,
  onEditSection,
  onMove,
  onCvTitleChange,
  onTemplateChange,
  onFetchPreviewHtml,
  onCoverTextChange,
  onCoverTitleChange,
  onCopy,
  onSave,
  onBack,
}: ReviewStepProps) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const sectionMap = preview ? new Map(preview.sections.map((s) => [s.section_id, s])) : new Map()
  const orderedSections = sectionOrder
    .map((id) => sectionMap.get(id))
    .filter((s): s is NonNullable<typeof s> => s !== undefined)
  const wordCount = coverText.trim() ? coverText.trim().split(/\s+/).length : 0

  return (
    <div className="space-y-6">
      {wantCv && preview && (
        <div className="space-y-5">
          <TailorSummary meta={preview.meta} />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-fg">Review CV section changes</h2>
              <p className="mt-1 text-sm text-fg-subtle">
                Accept, edit, or reorder sections. Rejected sections keep the original text.
              </p>
            </div>
            <div className="text-sm text-fg-subtle">
              {acceptedIds.size} of {preview.sections.length} accepted
            </div>
          </div>

          <div className="space-y-4">
            {orderedSections.map((section, idx) => (
              <SectionDiff
                key={section.section_id}
                section={section}
                accepted={acceptedIds.has(section.section_id)}
                onToggle={() => onToggle(section.section_id)}
                editedText={editedContent.get(section.section_id)}
                onEdit={(text) => onEditSection(section.section_id, text)}
                onMoveUp={() => onMove(section.section_id, -1)}
                onMoveDown={() => onMove(section.section_id, 1)}
                isFirst={idx === 0}
                isLast={idx === orderedSections.length - 1}
              />
            ))}
          </div>

          <div className="rounded-2xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-fg">PDF template</h3>
                <p className="mb-3 mt-0.5 text-xs text-fg-subtle">
                  The design applied to the saved CV and the cover letter PDF.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPreviewOpen(true)}
                className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-sm font-semibold text-fg-muted transition hover:bg-surface-strong hover:text-fg"
              >
                <EyeIcon className="h-4 w-4" />
                Preview
              </button>
            </div>
            <TemplatePicker value={templateId} onChange={onTemplateChange} />
            <TemplatePreviewModal
              open={previewOpen}
              templateId={templateId}
              onClose={() => setPreviewOpen(false)}
              onTemplateChange={onTemplateChange}
              fetchHtml={onFetchPreviewHtml}
            />
          </div>

          <div className="rounded-2xl border border-line bg-surface p-5">
            <label className="text-xs font-medium uppercase tracking-wide text-fg-muted">
              Saved CV title
            </label>
            <input
              value={cvTitle}
              onChange={(event) => onCvTitleChange(event.target.value)}
              placeholder="Tailored CV"
              className="mt-1.5 w-full rounded-lg border border-line px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
      )}

      {wantCover && (
        <div className="space-y-4 rounded-2xl border border-line bg-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-fg">Edit your cover letter</h2>
              <p className="mt-0.5 text-xs text-fg-subtle">
                Review and refine before saving. Changes are only saved when you click Save.
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-surface px-2.5 py-0.5 text-xs font-medium text-fg-subtle">
              {wordCount} words
            </span>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-fg-muted">Cover letter title (optional)</label>
            <input
              type="text"
              className="input w-full"
              placeholder="e.g. Cover letter for Spotify"
              value={coverTitle}
              onChange={(e) => onCoverTitleChange(e.target.value)}
            />
          </div>

          <textarea
            className="input min-h-[400px] w-full resize-y font-mono text-sm leading-relaxed"
            value={coverText}
            onChange={(e) => onCoverTextChange(e.target.value)}
            spellCheck
          />

          <button
            type="button"
            onClick={onCopy}
            className="inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 py-2.5 text-sm font-medium text-fg-muted hover:bg-surface-strong"
          >
            <ClipboardDocumentIcon className="h-4 w-4" />
            Copy text
          </button>
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="rounded-lg bg-surface px-4 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-strong disabled:opacity-50"
        >
          Start over
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saving || (wantCover && !coverText.trim())}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {saving && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
          {wantCv && wantCover ? 'Save CV & cover letter' : wantCv ? 'Save tailored PDF' : 'Save cover letter'}
        </button>
      </div>
    </div>
  )
}
