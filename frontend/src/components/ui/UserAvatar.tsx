interface Props {
  fullName: string | null | undefined
  email: string | null | undefined
  size?: 'sm' | 'md'
}

function getInitials(fullName: string | null | undefined, email: string | null | undefined): string {
  if (fullName?.trim()) {
    return fullName
      .trim()
      .split(/\s+/)
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }
  return (email?.[0] ?? '?').toUpperCase()
}

export default function UserAvatar({ fullName, email, size = 'md' }: Props) {
  const initials = getInitials(fullName, email)
  const sizeClass = size === 'sm' ? 'h-7 w-7 text-xs' : 'h-8 w-8 text-xs'

  return (
    <span
      className={`${sizeClass} flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 font-bold text-white shadow-sm select-none`}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}
