import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import type { ResumeComparison } from '../../../types'

interface Props {
  data: ResumeComparison | null
}

export default function ResumeComparisonChart({ data }: Props) {
  const chartData = useMemo(() => {
    if (!data) return []

    const rankedSkills = [...data.skill_details]
      .sort((a, b) => b.total_market_mentions - a.total_market_mentions)
      .slice(0, 8)
    const maxMentions = Math.max(...rankedSkills.map((skill) => skill.total_market_mentions), 1)

    return rankedSkills.map((skill) => ({
      skill: skill.skill,
      marketDemand: Math.round((skill.total_market_mentions / maxMentions) * 100),
      yourResume: skill.in_resume ? 100 : 0,
    }))
  }, [data])

  if (!data || chartData.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center md:h-72">
        <div className="text-center">
          <p className="text-sm text-gray-600">Upload a resume to see your skill comparison.</p>
          <Link to="/cvs" className="mt-2 inline-block text-sm font-medium text-primary-600 transition-colors duration-200 hover:text-primary-700">
            Upload resume
          </Link>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-gray-50 p-3">
          <p className="text-xs font-medium text-gray-500">Alignment</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{Math.round(data.overall_market_alignment_score)}%</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3">
          <p className="text-xs font-medium text-gray-500">Matched Skills</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{data.matched_skills.length}</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3">
          <p className="text-xs font-medium text-gray-500">Market Coverage</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{Math.round(data.skills_market_coverage_pct)}%</p>
        </div>
      </div>

      <div className="h-48 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis dataKey="skill" tick={{ fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Radar name="Market Demand" dataKey="marketDemand" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} strokeWidth={2} />
          <Radar name="Your Resume" dataKey="yourResume" stroke="#10b981" fill="#10b981" fillOpacity={0.3} strokeWidth={2} />
          <Legend wrapperStyle={{ paddingTop: '16px', fontSize: '12px' }} iconType="circle" />
          <Tooltip
            formatter={(value) => [`${value}%`, '']}
            contentStyle={CHART_TOOLTIP_STYLE}
          />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {data.missing_high_demand_skills.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase text-gray-500">Missing high-demand skills</p>
          <div className="flex flex-wrap gap-2">
            {data.missing_high_demand_skills.slice(0, 10).map((skill) => (
              <span key={skill} className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
