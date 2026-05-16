export function SkeletonCard() {
  return (
    <div className="space-y-3 rounded-2xl border border-gray-100 bg-white p-5">
      <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
      <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200" />
      <div className="h-3 w-2/3 animate-pulse rounded bg-gray-200" />
      <div className="flex gap-2 pt-2">
        <div className="h-6 w-16 animate-pulse rounded-full bg-gray-200" />
        <div className="h-6 w-20 animate-pulse rounded-full bg-gray-200" />
      </div>
    </div>
  )
}
