import { scorePassword } from '../../lib/passwordStrength'

export function PasswordStrengthMeter({ password }: { password: string }) {
  if (!password) return null
  const strength = scorePassword(password)

  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1">
        {[1, 2, 3].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              strength.score >= level
                ? level === 1 ? 'bg-red-500' : level === 2 ? 'bg-amber-500' : 'bg-green-500'
                : 'bg-surface'
            }`}
          />
        ))}
      </div>
      {strength.label && (
        <p className="text-xs text-fg-subtle">
          Strength: <span className={`font-medium ${strength.textColor}`}>{strength.label}</span>
        </p>
      )}
    </div>
  )
}
