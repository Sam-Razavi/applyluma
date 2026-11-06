import { ArrowPathIcon, CheckCircleIcon, PencilSquareIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { Link } from 'react-router-dom'
import { IntensitySelector } from '../IntensitySelector'
import type { CV, JobDescription } from '../../../types'
import type { DiscoveredJobDetail } from '../../../types/jobDiscovery'
import type { TailorIntensity } from '../../../types/tailor'
import type { CoverLetterTone } from '../../../types/coverLetter'

const TONE_OPTIONS: { value: CoverLetterTone; label: string; description: string }[] = [
  { value: 'formal', label: 'Formal', description: 'Professional, structured, 300–350 words' },
  { value: 'friendly', label: 'Friendly', description: 'Warm but professional, 300–350 words' },
  { value: 'concise', label: 'Concise', description: 'Short and direct, 200–250 words' },
]

interface SelectStepProps {
  cvs: CV[]
  jobs: JobDescription[]
  loading: boolean
  selectedCvId: string
  selectedJobId: string
  selectedCv: CV | undefined
  selectedJob: JobDescription | undefined
  rawJob: DiscoveredJobDetail | null
  rawJobPostingId: string | undefined
  wantCv: boolean
  wantCover: boolean
  intensity: TailorIntensity
  tone: CoverLetterTone
  onCvChange: (value: string) => void
  onJobChange: (value: string) => void
  onWantCvChange: (value: boolean) => void
  onWantCoverChange: (value: boolean) => void
  onIntensityChange: (value: TailorIntensity) => void
  onToneChange: (value: CoverLetterTone) => void
  onSubmit: () => void
  canSubmit: boolean
  submitting: boolean
  tailorAtLimit: boolean
  coverAtLimit: boolean
}

export function SelectStep({
  cvs,
  jobs,
  loading,
  selectedCvId,
  selectedJobId,
  selectedCv,
  selectedJob,
  rawJob,
  rawJobPostingId,
  wantCv,
  wantCover,
  intensity,
  tone,
  onCvChange,
  onJobChange,
  onWantCvChange,
  onWantCoverChange,
  onIntensityChange,
  onToneChange,
  onSubmit,
  canSubmit,
  submitting,
  tailorAtLimit,
  coverAtLimit,
}: SelectStepProps) {
  const submitLabel =
    wantCv && wantCover
      ? 'Tailor CV & write cover letter'
      : wantCv
        ? 'Tailor CV'
        : 'Write cover letter'

  return (
    <div className="space-y-6 rounded-2xl border border-line bg-surface p-6">
      <div>
        <h2 className="text-sm font-semibold text-fg-muted">Select source CV and target job</h2>
        <p className="mt-1 text-xs text-fg-subtle">
          Your original CV stays unchanged. A tailored copy and cover letter are created only after
          you save.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Selector
          label="Your CV"
          value={selectedCvId}
          onChange={onCvChange}
          loading={loading}
          emptyMessage="No CVs found"
          emptyHref="/cvs"
          emptyLinkLabel="Upload one"
          options={cvs.map((cv) => ({
            value: cv.id,
            label: `${cv.title}${cv.is_default ? ' (default)' : ''}`,
          }))}
        />
        {rawJobPostingId ? (
          <div className="rounded-lg border border-brand-100 bg-primary-900/20 px-3 py-2.5">
            <p className="text-xs font-medium uppercase tracking-wide text-accent-text">Target job</p>
            <p className="mt-1 text-sm font-semibold text-fg">
              {rawJob ? `${rawJob.title} @ ${rawJob.company}` : 'Loading discovered job'}
            </p>
          </div>
        ) : (
          <Selector
            label="Target job"
            value={selectedJobId}
            onChange={onJobChange}
            loading={loading}
            emptyMessage="No job descriptions found"
            emptyHref="/discover?tab=saved"
            emptyLinkLabel="Add one"
            options={jobs.map((job) => ({
              value: job.id,
              label: `${job.job_title} @ ${job.company_name}`,
            }))}
          />
        )}
      </div>

      {(selectedCv || selectedJob) && (
        <div className="flex flex-wrap gap-2">
          {selectedCv && <Pill>{selectedCv.title}</Pill>}
          {rawJob && <Pill>{`${rawJob.title} @ ${rawJob.company}`}</Pill>}
          {!rawJob && selectedJob && <Pill>{`${selectedJob.job_title} @ ${selectedJob.company_name}`}</Pill>}
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-fg-muted">What should we create?</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ToggleCard
            icon={SparklesIcon}
            title="Tailor CV"
            description="Rewrite your CV section by section for this job."
            checked={wantCv}
            onChange={onWantCvChange}
          />
          <ToggleCard
            icon={PencilSquareIcon}
            title="Write cover letter"
            description="Generate a matching cover letter you can edit and export."
            checked={wantCover}
            onChange={onWantCoverChange}
          />
        </div>
        {!wantCv && !wantCover && (
          <p className="text-sm text-chip-danger-fg">Choose at least one to continue.</p>
        )}
      </div>

      {wantCv && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-fg-muted">Tailoring intensity</h3>
          <IntensitySelector value={intensity} onChange={onIntensityChange} />
        </div>
      )}

      {wantCover && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-fg-muted">Cover letter tone</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {TONE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onToneChange(option.value)}
                className={`rounded-xl border p-3 text-left transition-colors ${
                  tone === option.value
                    ? 'border-primary-500/50 bg-primary-900/20 ring-1 ring-brand-400'
                    : 'border-line bg-surface hover:border-line-strong'
                }`}
              >
                <p className="text-sm font-semibold text-fg">{option.label}</p>
                <p className="mt-0.5 text-xs text-fg-subtle">{option.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={onSubmit}
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? (
          <>
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            Starting…
          </>
        ) : (
          <>
            <SparklesIcon className="h-4 w-4" />
            {submitLabel}
          </>
        )}
      </button>

      {(tailorAtLimit || coverAtLimit) && (
        <p className="text-sm text-chip-danger-fg">
          {tailorAtLimit && coverAtLimit
            ? 'Daily limits reached for both. Try again after the reset time or upgrade to premium.'
            : tailorAtLimit
              ? 'Daily CV tailoring limit reached. Turn off "Tailor CV" or try again after the reset time.'
              : 'Daily cover letter limit reached. Turn off "Write cover letter" or try again after the reset time.'}
        </p>
      )}
    </div>
  )
}

function ToggleCard({
  icon: Icon,
  title,
  description,
  checked,
  onChange,
}: {
  icon: typeof SparklesIcon
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      className={`flex items-start gap-3 rounded-xl border-2 p-4 text-left transition-colors ${
        checked ? 'border-brand-500 bg-primary-900/20' : 'border-line bg-surface hover:border-line-strong'
      }`}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${checked ? 'text-accent-text' : 'text-fg-subtle'}`} />
      <span className="min-w-0">
        <span className="flex items-center gap-2">
          <span className="text-sm font-semibold text-fg">{title}</span>
          {checked && <CheckCircleIcon className="h-4 w-4 text-accent-text" />}
        </span>
        <span className="mt-0.5 block text-xs leading-5 text-fg-subtle">{description}</span>
      </span>
    </button>
  )
}

interface SelectorProps {
  label: string
  value: string
  onChange: (value: string) => void
  loading: boolean
  emptyMessage: string
  emptyHref: string
  emptyLinkLabel: string
  options: { value: string; label: string }[]
}

function Selector({
  label,
  value,
  onChange,
  loading,
  emptyMessage,
  emptyHref,
  emptyLinkLabel,
  options,
}: SelectorProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium uppercase tracking-wide text-fg-muted">{label}</label>
      {loading ? (
        <div className="h-10 animate-pulse rounded-lg bg-track" />
      ) : options.length === 0 ? (
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-line-strong px-3 py-2.5 text-sm text-fg-subtle">
          {emptyMessage}
          <Link to={emptyHref} className="text-accent-text hover:underline">
            {emptyLinkLabel}
          </Link>
        </div>
      ) : (
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Choose...</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}

function Pill({ children }: { children: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-900/20 px-2.5 py-1 text-xs font-medium text-accent-text">
      <CheckCircleIcon className="h-3.5 w-3.5" />
      {children}
    </span>
  )
}
