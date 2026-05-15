export default function LoadingSkeleton() {
  return (
    <div className="h-48 animate-pulse md:h-72" aria-hidden="true">
      <div className="mb-4 flex h-36 items-end gap-2 md:h-60">
        {[40, 70, 50, 90, 60, 80, 45, 65].map((height, index) => (
          <div
            key={index}
            className="flex-1 rounded-t bg-gray-200"
            style={{ height: `${height}%`, minHeight: '80px' }}
          />
        ))}
      </div>
      <div className="flex justify-between">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((item) => (
          <div key={item} className="h-3 w-8 rounded bg-gray-200" />
        ))}
      </div>
    </div>
  )
}
