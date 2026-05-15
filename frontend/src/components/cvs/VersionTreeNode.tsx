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
            ? 'border-gray-200 bg-white hover:border-brand-200 hover:bg-brand-50'
            : 'border-gray-100 bg-gray-50 cursor-default'
        }`}
        style={{ marginLeft: `${depth * 18}px` }}
      >
        <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-blue-50">
          <DocumentTextIcon className="h-5 w-5 text-blue-500" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-gray-900">{node.title}</span>
          <span className="block text-xs text-gray-400">{formatDate(node.created_at)}</span>
        </span>
        {node.is_tailored && (
          <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
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
