import type { ReactNode } from 'react'

export const CATEGORY_AXIS_WIDTH = 116

/** Legend labels in the normal text colour: the dot carries the series colour. */
export function legendLabel(value: ReactNode): ReactNode {
  return <span style={{ color: 'var(--text-2)' }}>{value}</span>
}
