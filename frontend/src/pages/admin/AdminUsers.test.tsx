import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import AdminUsers from './AdminUsers'

const {
  mockListUsers,
  mockGetUserProfile,
  mockUpdateRole,
  mockUpdateActive,
  mockSendNotification,
  mockGetUserActivity,
  mockDeleteUser,
  mockSendPasswordReset,
  mockVerifyUser,
  mockUpdateLimits,
  mockGetUserSignupsDaily,
  mockGetUserFunnel,
} = vi.hoisted(() => ({
  mockListUsers: vi.fn(),
  mockGetUserProfile: vi.fn(),
  mockUpdateRole: vi.fn(),
  mockUpdateActive: vi.fn(),
  mockSendNotification: vi.fn(),
  mockGetUserActivity: vi.fn(),
  mockDeleteUser: vi.fn(),
  mockSendPasswordReset: vi.fn(),
  mockVerifyUser: vi.fn(),
  mockUpdateLimits: vi.fn(),
  mockGetUserSignupsDaily: vi.fn(),
  mockGetUserFunnel: vi.fn(),
}))

vi.mock('../../services/adminApi', () => ({
  adminApi: {
    listUsers: mockListUsers,
    getUserProfile: mockGetUserProfile,
    updateRole: mockUpdateRole,
    updateActive: mockUpdateActive,
    sendNotification: mockSendNotification,
    getUserActivity: mockGetUserActivity,
    deleteUser: mockDeleteUser,
    sendPasswordReset: mockSendPasswordReset,
    verifyUser: mockVerifyUser,
    updateLimits: mockUpdateLimits,
    getUserSignupsDaily: mockGetUserSignupsDaily,
    getUserFunnel: mockGetUserFunnel,
  },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const users = [
  {
    id: 'u1',
    email: 'active@example.com',
    full_name: 'Active User',
    role: 'user' as const,
    is_active: true,
    is_verified: true,
    subscription_status: null,
    created_at: '2026-01-01T00:00:00Z',
    last_login_at: '2026-07-10T12:00:00Z',
    login_count: 5,
  },
  {
    id: 'u2',
    email: 'never-logged-in@example.com',
    full_name: 'Never Login',
    role: 'user' as const,
    is_active: true,
    is_verified: false,
    subscription_status: null,
    created_at: '2026-02-01T00:00:00Z',
    last_login_at: null,
    login_count: 0,
  },
]

const profile = {
  ...users[0],
  auth_provider: 'local',
  avatar_url: null,
  stripe_customer_id: null,
  stripe_subscription_id: null,
  subscription_ends_at: null,
  updated_at: '2026-07-10T12:00:00Z',
  daily_tailor_limit_override: null,
  activity: {
    cvs: 2,
    tailored_cvs: 1,
    job_descriptions: 1,
    applications: 3,
    saved_jobs: 4,
    tailor_jobs: 5,
    tailor_jobs_failed: 0,
    cover_letters: 1,
    cover_letters_failed: 0,
    notifications: 2,
    unread_notifications: 1,
  },
  ai_costs: {
    last_30_days_usd: 1.23,
    all_time_usd: 9.87,
    all_time_calls: 42,
  },
}

const activityPage1 = {
  items: [
    { type: 'cv_uploaded', title: 'My CV', status: null, timestamp: '2026-07-01T00:00:00Z', ref_id: 'r1' },
  ],
  total: 1,
  page: 1,
  size: 25,
}

async function openDrawer() {
  const viewButtons = await screen.findAllByRole('button', { name: 'View' })
  fireEvent.click(viewButtons[0])
  await screen.findByText('AI Spend')
}

describe('AdminUsers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListUsers.mockResolvedValue({ items: users, total: 2, page: 1, size: 25 })
    mockGetUserProfile.mockResolvedValue(profile)
    mockGetUserActivity.mockResolvedValue(activityPage1)
    mockGetUserSignupsDaily.mockResolvedValue([
      { date: '2026-07-10', count: 2, verified_count: 1 },
      { date: '2026-07-11', count: 1, verified_count: 0 },
    ])
    mockGetUserFunnel.mockResolvedValue({
      registered: 59,
      verified: 12,
      has_cv: 9,
      attempted_tailor: 0,
      completed_tailor: 0,
    })
  })

  it('shows the signup funnel with counts fetched from the API', async () => {
    render(<AdminUsers />)

    expect(await screen.findByText('Registered')).toBeInTheDocument()
    expect(screen.getByText('59')).toBeInTheDocument()
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Uploaded a CV')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument()
    expect(screen.getByText('Attempted tailor')).toBeInTheDocument()
    expect(screen.getByText('Completed tailor')).toBeInTheDocument()
    expect(mockGetUserSignupsDaily).toHaveBeenCalledWith(30)
  })

  it('shows a Last login column, formatted for logged-in users and a dash otherwise', async () => {
    render(<AdminUsers />)
    await screen.findByText('active@example.com')

    const row1 = screen.getByText('active@example.com').closest('tr') as HTMLElement
    expect(within(row1).getByText('Jul 10, 2026')).toBeInTheDocument()

    const row2 = screen.getByText('never-logged-in@example.com').closest('tr') as HTMLElement
    const cells = within(row2).getAllByRole('cell')
    expect(cells[6]).toHaveTextContent('—') // Last login column
  })

  it('drawer shows AI spend and the activity timeline', async () => {
    render(<AdminUsers />)
    await openDrawer()

    expect(screen.getByText('$1.23')).toBeInTheDocument()
    expect(screen.getByText('$9.87')).toBeInTheDocument()

    await waitFor(() => expect(mockGetUserActivity).toHaveBeenCalledWith('u1', 1))
    expect(await screen.findByText('CV uploaded')).toBeInTheDocument()
    expect(screen.getByText('My CV')).toBeInTheDocument()
  })

  it('delete requires typing the exact email before the confirm button enables', async () => {
    mockDeleteUser.mockResolvedValue(undefined)
    render(<AdminUsers />)
    await openDrawer()

    fireEvent.click(screen.getByRole('button', { name: 'Delete user' }))
    // Headless UI's Dialog marks background content aria-hidden while open,
    // so only the dialog's own controls are queryable by role at this point.
    const dialog = await screen.findByRole('dialog')
    const dialogConfirm = within(dialog).getByRole('button', { name: 'Delete user' })
    expect(dialogConfirm).toBeDisabled()

    const input = within(dialog).getByRole('textbox')
    fireEvent.change(input, { target: { value: 'wrong@example.com' } })
    expect(dialogConfirm).toBeDisabled()

    fireEvent.change(input, { target: { value: 'active@example.com' } })
    expect(dialogConfirm).not.toBeDisabled()

    fireEvent.click(dialogConfirm)
    await waitFor(() => expect(mockDeleteUser).toHaveBeenCalledWith('u1'))
  })

  it('saves and clears the daily tailor limit override', async () => {
    mockGetUserProfile.mockReset()
    mockGetUserProfile.mockResolvedValueOnce(profile)
    mockGetUserProfile.mockResolvedValueOnce({ ...profile, daily_tailor_limit_override: 7 })
    mockUpdateLimits.mockResolvedValueOnce({ ...profile, daily_tailor_limit_override: 7 })
    mockUpdateLimits.mockResolvedValueOnce({ ...profile, daily_tailor_limit_override: null })

    render(<AdminUsers />)
    await openDrawer()

    const limitInput = screen.getByPlaceholderText('Role default')
    fireEvent.change(limitInput, { target: { value: '7' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(mockUpdateLimits).toHaveBeenCalledWith('u1', 7))

    const clearButton = await waitFor(() => {
      const btn = screen.getByRole('button', { name: 'Clear' })
      expect(btn).not.toBeDisabled()
      return btn
    })
    fireEvent.click(clearButton)
    await waitFor(() => expect(mockUpdateLimits).toHaveBeenCalledWith('u1', null))
  })
})
