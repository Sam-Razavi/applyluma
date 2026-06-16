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
      ? 'bg-[rgba(52,195,143,0.14)] text-emerald-300'
      : 'bg-[rgba(229,72,77,0.12)] text-red-300 hover:bg-[rgba(229,72,77,0.12)]'

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
  if (total === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
        <h3 className="text-sm font-semibold text-white/90">Skills match</h3>
        <p className="mt-2 text-xs text-white/30">
          Upload a CV so AI can compare your skills against this role.
        </p>
      </div>
    )
  }

  async function copySkill(skill: string) {
    await navigator.clipboard.writeText(skill)
    toast.success('Skill copied')
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
      <h3 className="text-sm font-semibold text-white/90">
        {matchedSkills.length} of {total} required skills matched
      </h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold text-emerald-300">Matched</p>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.length ? (
              matchedSkills.map((skill) => (
                <SkillPill key={skill} skill={skill} variant="matched" />
              ))
            ) : (
              <span className="text-xs text-white/30">None yet</span>
            )}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold text-red-300">Missing</p>
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
              <span className="text-xs text-white/30">No gaps found</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
