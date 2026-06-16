export function SkeletonCard() {
  return (
    <div className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.04] p-5">
      <div className="h-4 w-3/4 animate-pulse rounded bg-white/[0.06]" />
      <div className="h-3 w-1/2 animate-pulse rounded bg-white/[0.06]" />
      <div className="h-3 w-2/3 animate-pulse rounded bg-white/[0.06]" />
      <div className="flex gap-2 pt-2">
        <div className="h-6 w-16 animate-pulse rounded-full bg-white/[0.06]" />
        <div className="h-6 w-20 animate-pulse rounded-full bg-white/[0.06]" />
      </div>
    </div>
  )
}
