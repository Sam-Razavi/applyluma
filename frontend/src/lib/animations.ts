export const spring = {
  snappy: { type: 'spring', damping: 30, stiffness: 300 },
  gentle: { type: 'spring', damping: 25, stiffness: 200 },
} as const

export const ease = {
  quick: { duration: 0.15 },
  standard: { duration: 0.25 },
  slow: { duration: 0.4 },
} as const

export const staggerItem = (i: number) => ({ delay: i * 0.04, duration: 0.2 })

export const variants = {
  fadeIn: { initial: { opacity: 0 }, animate: { opacity: 1 } },
  slideUp: { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 } },
  slideLeft: { initial: { x: '-100%' }, animate: { x: 0 } },
  slideRight: { initial: { x: '100%' }, animate: { x: 0 } },
  scaleIn: { initial: { opacity: 0, scale: 0.95 }, animate: { opacity: 1, scale: 1 } },
} as const
