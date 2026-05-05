export interface User {
  id: string
  email: string
  created_at: string
  updated_at: string
}

export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}
