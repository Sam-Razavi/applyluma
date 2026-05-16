import toast from 'react-hot-toast'

interface Props {
  matchedSkills: string[]
  missingSkills: string[]
}

function SkillPill({
  skill,
  variant,
  onClick,
}: {
  skill: string
  variant: 'matched' | 'missing'
  onClick?: () => void
}) {
  const classes =
    variant === 'matched'
      ? 'bg-green-50 text-green-700'
      : 'bg-red-50 text-red-700 hover:bg-red-100'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}
    >
      {skill}
    </button>
  )
}

export default function SkillsBreakdown({ matchedSkills, missingSkills }: Props) {
  const total = matchedSkills.length + missingSkills.length
  if (total === 0) return null

  async function copySkill(skill: string) {
    await navigator.clipboard.writeText(skill)
    toast.success('Skill copied')
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">
        {matchedSkills.length} of {total} required skills matched
      </h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold text-green-700">Matched</p>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.length ? (
              matchedSkills.map((skill) => (
                <SkillPill key={skill} skill={skill} variant="matched" />
              ))
            ) : (
              <span className="text-xs text-gray-400">None yet</span>
            )}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold text-red-700">Missing</p>
          <div className="flex flex-wrap gap-1.5">
            {missingSkills.length ? (
              missingSkills.map((skill) => (
                <SkillPill
                  key={skill}
                  skill={skill}
                  variant="missing"
                  onClick={() => void copySkill(skill)}
                />
              ))
            ) : (
              <span className="text-xs text-gray-400">No gaps found</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
