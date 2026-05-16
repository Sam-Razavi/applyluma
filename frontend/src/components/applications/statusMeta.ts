import type { ApplicationStatus } from '../../types/application'

export const STATUS_META: Record<ApplicationStatus, { label: string; color: string }> = {
  wishlist: { label: 'Wishlist', color: 'bg-gray-400' },
  applied: { label: 'Applied', color: 'bg-blue-500' },
  phone_screen: { label: 'Phone Screen', color: 'bg-yellow-500' },
  interview: { label: 'Interview', color: 'bg-purple-500' },
  offer: { label: 'Offer', color: 'bg-green-500' },
  rejected: { label: 'Rejected', color: 'bg-red-500' },
  withdrawn: { label: 'Withdrawn', color: 'bg-slate-500' },
}
