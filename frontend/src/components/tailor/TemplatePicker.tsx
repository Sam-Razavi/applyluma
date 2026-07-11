import type { CvTemplateId } from '../../types/tailor'
import { TEMPLATE_OPTIONS } from './templateOptions'

// Fixed miniature previews of the PDF templates — intentionally hardcoded
// colors matching the render templates, independent of the app theme.
function NordicThumb() {
  return (
    <div className="h-24 w-full overflow-hidden rounded-md border border-line bg-white">
      <div className="border-b-2 border-[#0B7F89] bg-[#163A5F] px-2 pb-1.5 pt-2">
        <div className="h-1.5 w-14 rounded-sm bg-white/90" />
        <div className="mt-1 h-1 w-20 rounded-sm bg-[#C9E2EA]" />
      </div>
      <div className="space-y-1 px-2 py-1.5">
        <div className="h-1 w-10 rounded-sm bg-[#163A5F]" />
        <div className="h-1 w-full rounded-sm bg-gray-300" />
        <div className="h-1 w-5/6 rounded-sm bg-gray-300" />
        <div className="mt-1 h-4 w-full rounded-sm bg-[#EAF2F5]" />
      </div>
    </div>
  )
}

function ClassicThumb() {
  return (
    <div className="h-24 w-full overflow-hidden rounded-md border border-line bg-white">
      <div className="border-b-2 border-gray-900 px-2 pb-1.5 pt-2">
        <div className="h-1.5 w-14 rounded-sm bg-gray-900" />
        <div className="mt-1 h-1 w-20 rounded-sm bg-gray-500" />
      </div>
      <div className="space-y-1 px-2 py-1.5">
        <div className="h-1 w-10 rounded-sm bg-gray-700" />
        <div className="h-1 w-full rounded-sm bg-gray-300" />
        <div className="h-1 w-5/6 rounded-sm bg-gray-300" />
        <div className="h-1 w-10 rounded-sm bg-gray-700" />
        <div className="h-1 w-4/6 rounded-sm bg-gray-300" />
      </div>
    </div>
  )
}

function ModernThumb() {
  return (
    <div className="h-24 w-full overflow-hidden rounded-md border border-line bg-white">
      <div className="border-b-2 border-[#6D28D9] px-2 pb-1.5 pt-2">
        <div className="h-1.5 w-14 rounded-sm bg-[#4C1D95]" />
        <div className="mt-1 h-1 w-20 rounded-sm bg-gray-500" />
      </div>
      <div className="space-y-1 px-2 py-1.5">
        <div className="h-1 w-10 rounded-sm bg-[#4C1D95]" />
        <div className="flex gap-1">
          <div className="h-2 w-8 rounded-sm bg-[#F3EEFB]" />
          <div className="h-2 w-6 rounded-sm bg-[#F3EEFB]" />
          <div className="h-2 w-7 rounded-sm bg-[#F3EEFB]" />
        </div>
        <div className="h-1 w-full rounded-sm bg-gray-300" />
        <div className="h-1 w-5/6 rounded-sm bg-gray-300" />
      </div>
    </div>
  )
}

function ExecutiveThumb() {
  return (
    <div className="h-24 w-full overflow-hidden rounded-md border border-line bg-white">
      <div className="flex flex-col items-center border-b border-gray-800 px-2 pb-1.5 pt-2">
        <div className="h-1.5 w-14 rounded-sm bg-gray-800" />
        <div className="mt-1 h-1 w-16 rounded-sm bg-[#6E3B3B]" />
      </div>
      <div className="space-y-1 px-2 py-1.5">
        <div className="mx-auto h-1 w-10 rounded-sm bg-gray-700" />
        <div className="mx-auto h-px w-6 bg-[#6E3B3B]" />
        <div className="h-1 w-full rounded-sm bg-gray-300" />
        <div className="h-1 w-5/6 rounded-sm bg-gray-300" />
        <div className="h-1 w-4/6 rounded-sm bg-gray-300" />
      </div>
    </div>
  )
}

const THUMBS: Record<CvTemplateId, () => JSX.Element> = {
  nordic: NordicThumb,
  classic: ClassicThumb,
  modern: ModernThumb,
  executive: ExecutiveThumb,
}

interface Props {
  value: CvTemplateId
  onChange: (value: CvTemplateId) => void
}

export function TemplatePicker({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {TEMPLATE_OPTIONS.map((option) => {
        const Thumb = THUMBS[option.value]
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
            className={`rounded-xl border-2 p-3 text-left transition-colors ${
              value === option.value
                ? 'border-brand-500 bg-primary-900/20'
                : 'border-line bg-surface hover:border-line-strong'
            }`}
          >
            <Thumb />
            <p className="mt-2 text-sm font-semibold text-fg">{option.label}</p>
            <p className="mt-0.5 text-xs leading-5 text-fg-subtle">{option.description}</p>
          </button>
        )
      })}
    </div>
  )
}
