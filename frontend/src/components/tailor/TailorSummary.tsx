import type { TailorMeta } from '../../types/tailor'

interface Props {
  meta: TailorMeta
}

export function TailorSummary({ meta }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 rounded-2xl border border-line bg-surface p-5 md:grid-cols-3">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Intensity</p>
        <p className="mt-1 text-sm font-semibold capitalize text-fg">
          {meta.intensity_applied || 'medium'}
        </p>
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-fg-subtle">
          Keywords added
        </p>
        <p className="mt-1 text-sm text-fg-muted">
          {meta.keywords_added.length > 0 ? meta.keywords_added.join(', ') : 'None reported'}
        </p>
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-fg-subtle">
          Already present
        </p>
        <p className="mt-1 text-sm text-fg-muted">
          {meta.keywords_already_present.length > 0
            ? meta.keywords_already_present.join(', ')
            : 'None reported'}
        </p>
      </div>
    </div>
  )
}
