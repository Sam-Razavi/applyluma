import toast from 'react-hot-toast'

interface Props {
  matchedSkills: string[]
  missingSkills: string[]
  onSkillClick?: (skill: string) => void
}

function SkillPill({
  skill,
  variant,
  onClick,
  title,
}: {
  skill: string
  variant: 'matched' | 'missing'
  onClick?: () => void
  title?: string
}) {
  const classes =
    variant === 'matched'
      ? 'bg-chip-success text-chip-success-fg'
      : 'bg-chip-danger text-chip-danger-fg hover:bg-chip-danger'

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}
    >
      {skill}
    </button>
  )
}

export default function SkillsBreakdown({ matchedSkills, missingSkills, onSkillClick }: Props) {
  const total = matchedSkills.length + missingSkills.length
  if (total === 0) {
    return (
      <div className="rounded-xl border border-line bg-surface p-4">
        <h3 className="text-sm font-semibold text-fg">Skills match</h3>
        <p className="mt-2 text-xs text-fg-subtle">
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
    <div className="rounded-xl border border-line bg-surface p-4">
      <h3 className="text-sm font-semibold text-fg">
        {matchedSkills.length} of {total} required skills matched
      </h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold text-chip-success-fg">Matched</p>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.length ? (
              matchedSkills.map((skill) => (
                <SkillPill
                  key={skill}
                  skill={skill}
                  variant="matched"
                  onClick={onSkillClick ? () => onSkillClick(skill) : undefined}
                  title={onSkillClick ? 'Filter jobs by this skill' : undefined}
                />
              ))
            ) : (
              <span className="text-xs text-fg-subtle">None yet</span>
            )}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold text-chip-danger-fg">Missing</p>
          <div className="flex flex-wrap gap-1.5">
            {missingSkills.length ? (
              missingSkills.map((skill) => (
                <SkillPill
                  key={skill}
                  skill={skill}
                  variant="missing"
                  onClick={
                    onSkillClick ? () => onSkillClick(skill) : () => void copySkill(skill)
                  }
                  title={onSkillClick ? 'Filter jobs by this skill' : 'Copy skill'}
                />
              ))
            ) : (
              <span className="text-xs text-fg-subtle">No gaps found</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
