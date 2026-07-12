import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { LightBulbIcon } from '@heroicons/react/24/outline'
import { CV_TIPS } from '../../lib/cvTips'
import { ease } from '../../lib/animations'

const ROTATE_INTERVAL_MS = 5500

export function TailorTips() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * CV_TIPS.length))
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % CV_TIPS.length)
    }, ROTATE_INTERVAL_MS)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  return (
    <div className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex items-start gap-3">
        <LightBulbIcon className="mt-0.5 h-5 w-5 flex-shrink-0 text-accent-text" />
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-text">Tip</p>
          <div className="mt-1 min-h-[2.5rem]">
            <motion.p
              key={index}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={ease.standard}
              className="text-sm text-fg-subtle"
            >
              {CV_TIPS[index]}
            </motion.p>
          </div>
        </div>
      </div>
    </div>
  )
}
