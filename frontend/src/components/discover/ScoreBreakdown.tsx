import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import { MATCH_WEIGHTS, scoreBand } from '../../utils/matchScore'

interface Props {
  skillsMatch: number | null
  experienceMatch: number | null
  salaryMatchScore: number | null
  educationMatch: number | null
  locationMatch: number | null
  explanation: string | null
}

const ROWS = [
  { key: 'skills_match', label: 'Skills' },
  { key: 'experience_match', label: 'Experience' },
  { key: 'salary_match_score', label: 'Salary' },
  { key: 'education_match', label: 'Education' },
  { key: 'location_match', label: 'Location' },
] as const

function barColor(value: number): string {
  if (value >= 80) return 'bg-green-500'
  if (value >= 60) return 'bg-yellow-400'
  return 'bg-red-400'
}

export default function ScoreBreakdown({
  skillsMatch,
  experienceMatch,
  salaryMatchScore,
  educationMatch,
  locationMatch,
  explanation,
}: Props) {
  const [open, setOpen] = useState(true)
  const values = {
    skills_match: skillsMatch,
    experience_match: experienceMatch,
    salary_match_score: salaryMatchScore,
    education_match: educationMatch,
    location_match: locationMatch,
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="text-sm font-semibold text-gray-900">Score breakdown</span>
        <ChevronDownIcon
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="mt-4 space-y-3">
          {ROWS.map((row) => {
            const value = values[row.key]
            if (value === null) return null
            const pct = Math.round(value)
            return (
              <div key={row.key} className="space-y-1">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-gray-700">
                    {row.label} <span className="text-gray-400">({MATCH_WEIGHTS[row.key]}%)</span>
                  </span>
                  <span className="text-gray-500">
                    {scoreBand(value)} - {pct}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-gray-100">
                  <div className={`h-full rounded-full ${barColor(pct)}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
          {explanation && <p className="pt-1 text-xs text-gray-500">{explanation}</p>}
        </div>
      )}
    </div>
  )
}
