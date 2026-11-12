interface CategoryTickProps {
  x?: number | string
  y?: number | string
  payload?: { value?: string | number }
}

const MAX_LABEL = 16

/** Y-axis label for horizontal bar charts: one line, shortened if needed.
 *  The default tick wraps long names onto two lines, which collide when
 *  every row is labelled. */
export function CategoryTick({ x = 0, y = 0, payload }: CategoryTickProps) {
  const label = String(payload?.value ?? '')
  const short = label.length > MAX_LABEL ? `${label.slice(0, MAX_LABEL - 1)}…` : label
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fontSize={12} fill="var(--text-2)">
      <title>{label}</title>
      {short}
    </text>
  )
}
