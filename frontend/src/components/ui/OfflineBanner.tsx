import { AnimatePresence, motion } from 'framer-motion'
import { SignalSlashIcon } from '@heroicons/react/24/outline'
import { useOnlineStatus } from '../../hooks/useOnlineStatus'

export function OfflineBanner() {
  const isOnline = useOnlineStatus()

  return (
    <AnimatePresence>
      {!isOnline && (
        <motion.div
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.25 }}
          role="status"
          className="fixed left-0 right-0 top-0 z-50 flex items-center justify-center gap-2 bg-chip-warn px-4 py-2 text-center text-sm font-medium text-chip-warn-fg shadow-sm"
        >
          <SignalSlashIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
          You're offline — we'll reconnect automatically.
        </motion.div>
      )}
    </AnimatePresence>
  )
}
