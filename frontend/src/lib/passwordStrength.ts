// Client-side mirror of the backend's most-common-passwords blocklist
// (app/core/password_policy.py is authoritative; a short list is enough here).
const COMMON_PASSWORDS = new Set([
  'password',
  'password1',
  'password123',
  'passw0rd',
  '12345678',
  '123456789',
  'qwerty123',
  'iloveyou1',
  'welcome1',
  'letmein1',
])

export interface PasswordStrength {
  score: 0 | 1 | 2 | 3
  label: string
  textColor: string
}

export function scorePassword(password: string): PasswordStrength {
  if (!password) return { score: 0, label: '', textColor: '' }
  const meta: { label: string; textColor: string }[] = [
    { label: '', textColor: '' },
    { label: 'Weak', textColor: 'text-chip-danger-fg' },
    { label: 'Fair', textColor: 'text-chip-warn-fg' },
    { label: 'Strong', textColor: 'text-chip-success-fg' },
  ]
  if (COMMON_PASSWORDS.has(password.toLowerCase())) {
    return { score: 1, ...meta[1] } as PasswordStrength
  }
  let score = 0
  if (password.length >= 8) score++
  if (password.length >= 12) score++
  if (/[A-Z]/.test(password) && /[0-9]/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++
  const capped = Math.min(score, 3) as 0 | 1 | 2 | 3
  return { score: capped, ...meta[capped] } as PasswordStrength
}
