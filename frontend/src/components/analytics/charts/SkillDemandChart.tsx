import { useMemo } from 'react'
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../../styles/analytics-colors'
import { formatNumber } from '../../../utils/formatters'
import { CATEGORY_AXIS_WIDTH, legendLabel } from './chartHelpers'
import { CategoryTick } from './chartParts'
import type { SkillDemand } from '../../../types'

interface Props {
  data: SkillDemand[]
}

// One hue in two strengths: the pair reads as "the same skill, then and now".
const THIS_WEEK = CHART_COLORS[0]
const LAST_WEEK = 'rgba(59, 130, 246, 0.4)'

export default function SkillDemandChart({ data }: Props) {
  const chartData = useMemo(
    () =>
      data.slice(0, 8).map((skill) => ({
        skill: skill.skill,
        thisWeek: skill.mentions_this_week,
        lastWeek: skill.mentions_last_week,
      })),
    [data],
  )

  return (
    <>
      <div className="h-64 w-full md:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 16, left: 8, bottom: 5 }} barGap={2} barCategoryGap="24%">
          <XAxis type="number" allowDecimals={false} tick={CHART_AXIS_TICK} axisLine={{ stroke: 'var(--glass-border-strong)' }} tickLine={false} />
          <YAxis type="category" dataKey="skill" width={CATEGORY_AXIS_WIDTH} interval={0} tick={<CategoryTick />} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value, name) => [`${formatNumber(Number(value))} job ads`, name]}
            contentStyle={CHART_TOOLTIP_STYLE}
            cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
          />
          <Legend itemSorter={null} formatter={legendLabel} wrapperStyle={{ paddingTop: '8px', fontSize: '12px' }} iconType="circle" />
          <Bar dataKey="thisWeek" name="This week" fill={THIS_WEEK} radius={[0, 4, 4, 0]} />
          <Bar dataKey="lastWeek" name="Last week" fill={LAST_WEEK} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p id="skill-demand-desc" className="sr-only">
        Bar chart comparing this week's and last week's job ads for the most requested skills.
      </p>
    </>
  )
}
