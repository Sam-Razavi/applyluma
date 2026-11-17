import type { ApplicationAnalytics, ApplicationInsights } from '../../../types/application'

export const pct = (rate: number): string => `${Math.round(rate * 100)}%`

/** Week-on-week change in applications sent, as a percent. null when there is nothing to compare. */
export function weeklyChangePct(insights: Pick<ApplicationInsights, 'applied_last_7d' | 'applied_prev_7d'>): number | null {
  if (insights.applied_prev_7d === 0) return null
  return ((insights.applied_last_7d - insights.applied_prev_7d) / insights.applied_prev_7d) * 100
}

/** Plain-language read-out of the numbers, shown above the charts. */
export function buildSummary(
  analytics: Pick<ApplicationAnalytics, 'response_rate' | 'average_response_days'>,
  insights: ApplicationInsights,
): string[] {
  if (insights.submitted === 0) {
    return [
      `You have ${insights.wishlist} job${insights.wishlist === 1 ? '' : 's'} on your wishlist. Move one to Applied and your stats start filling in.`,
    ]
  }

  const lines: string[] = []
  const sent = insights.submitted === 1 ? '1 application' : `${insights.submitted} applications`
  lines.push(
    insights.applied_last_7d > 0
      ? `You have sent ${sent} so far, ${insights.applied_last_7d} of them in the last 7 days.`
      : `You have sent ${sent} so far, none in the last 7 days.`,
  )

  let replies = `${pct(analytics.response_rate)} have had a reply and ${pct(insights.interview_rate)} reached an interview`
  if (analytics.average_response_days != null) {
    replies += `; replies take about ${analytics.average_response_days.toFixed(1)} days`
  }
  lines.push(`${replies}.`)

  if (insights.awaiting_reply > 0) {
    const n = insights.awaiting_reply
    lines.push(
      `${n} application${n === 1 ? ' has' : 's have'} had no reply for ${insights.awaiting_reply_days}+ days. A short follow-up is worth sending.`,
    )
  }

  return lines
}
