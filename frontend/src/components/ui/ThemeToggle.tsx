import { MoonIcon, SunIcon } from '@heroicons/react/24/outline'
import { useThemeStore } from '../../stores/theme'

interface Props {
  className?: string
}

// One-tap light/dark switch. Shows the icon of the mode you would switch TO.
export default function ThemeToggle({ className = '' }: Props) {
  const dark = useThemeStore((s) => s.dark)
  const toggle = useThemeStore((s) => s.toggle)
  const Icon = dark ? SunIcon : MoonIcon
  const label = dark ? 'Switch to light mode' : 'Switch to dark mode'

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className={`inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors duration-200 hover:bg-surface-strong hover:text-fg focus:outline-none focus:ring-2 focus:ring-brand-500 ${className}`}
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
    </button>
  )
}
