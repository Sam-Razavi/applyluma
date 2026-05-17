import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

export function FadeIn({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.div
      className="w-full min-w-0"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay }}
    >
      {children}
    </motion.div>
  )
}
