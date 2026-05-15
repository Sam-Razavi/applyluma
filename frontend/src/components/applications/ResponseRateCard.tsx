import KPICard from '../analytics/KPICard'

interface Props {
  responseRate: number
  offerRate: number
  averageResponseDays: number | null
}

export default function ResponseRateCard({
  responseRate,
  offerRate,
  averageResponseDays,
}: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <KPICard
        title="Response rate"
        value={responseRate * 100}
        format="percentage"
        icon="trending-up"
      />
      <KPICard
        title="Offer rate"
        value={offerRate * 100}
        format="percentage"
        icon="briefcase"
      />
      <div className="md:col-span-2 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-500 shadow-sm">
        Average response time:{' '}
        <span className="font-semibold text-gray-900">
          {averageResponseDays == null ? 'n/a' : `${averageResponseDays.toFixed(1)} days`}
        </span>
      </div>
    </div>
  )
}
