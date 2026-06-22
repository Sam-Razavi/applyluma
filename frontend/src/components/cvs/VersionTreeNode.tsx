import { DocumentTextIcon } from '@heroicons/react/24/outline'
import type { CVVersionNode } from '../../types'

interface Props {
  node: CVVersionNode
  depth?: number
  onViewDiff: (node: CVVersionNode) => void
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function VersionTreeNode({ node, depth = 0, onViewDiff }: Props) {
  const canViewDiff = node.is_tailored

  return (
    <div>
      <button
        type="button"
        onClick={() => canViewDiff && onViewDiff(node)}
        disabled={!canViewDiff}
        className={`flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left transition ${
          canViewDiff
            ? 'border-line bg-surface hover:border-primary-600/40 hover:bg-primary-900/20'
            : 'border-line bg-surface cursor-default'
        }`}
        style={{ marginLeft: `${depth * 18}px` }}
      >
        <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-chip-accent">
          <DocumentTextIcon className="h-5 w-5 text-blue-500" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-fg">{node.title}</span>
          <span className="block text-xs text-fg-subtle">{formatDate(node.created_at)}</span>
        </span>
        {node.is_tailored && (
          <span className="rounded-full bg-primary-900/30 px-2 py-0.5 text-xs font-semibold text-accent-text">
            Tailored
          </span>
        )}
      </button>

      {node.children.length > 0 && (
        <div className="mt-2 space-y-2">
          {node.children.map((child) => (
            <VersionTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onViewDiff={onViewDiff}
            />
          ))}
        </div>
      )}
    </div>
  )
}
