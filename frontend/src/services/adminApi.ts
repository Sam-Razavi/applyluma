import client from '../api/client'

export interface AdminOverviewStats {
  total_users: number
  premium_users: number
  admin_users: number
  new_users_this_week: number
  total_cvs: number
  total_job_descriptions: number
  total_applications: number
  total_tailor_jobs: number
  tailor_jobs_complete: number
  tailor_jobs_failed: number
  tailor_jobs_pending: number
  total_cover_letters: number
}

export interface AdminUserRow {
  id: string
  email: string
  full_name: string | null
  role: 'user' | 'premium' | 'admin'
  is_active: boolean
  is_verified: boolean
  subscription_status: string | null
  created_at: string
}

export interface AdminUserListResponse {
  items: AdminUserRow[]
  total: number
  page: number
  size: number
}

export const adminApi = {
  getStats(): Promise<AdminOverviewStats> {
    return client.get('/api/v1/admin/stats').then((r) => r.data)
  },

  listUsers(params: {
    search?: string
    role?: string
    page?: number
    size?: number
  }): Promise<AdminUserListResponse> {
    return client.get('/api/v1/admin/users', { params }).then((r) => r.data)
  },

  updateRole(userId: string, role: string): Promise<AdminUserRow> {
    return client.patch(`/api/v1/admin/users/${userId}/role`, { role }).then((r) => r.data)
  },

  updateActive(userId: string, is_active: boolean): Promise<AdminUserRow> {
    return client.patch(`/api/v1/admin/users/${userId}/active`, { is_active }).then((r) => r.data)
  },

  sendNotification(userId: string, title: string, body: string): Promise<void> {
    return client
      .post(`/api/v1/admin/users/${userId}/notify`, { title, body })
      .then(() => undefined)
  },
}
