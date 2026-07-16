export interface AdminOverview {
  users: number
  active_users: number
  tracks: number
  published_tracks: number
  lessons: number
  lesson_completions: number
  issued_certificates: number
  awarded_badges: number
}

export type UserStatus = "active" | "inactive" | "blocked"

export interface AdminUser {
  id: string
  name: string
  email: string
  role: "admin" | "student"
  status: UserStatus
  last_login: string | null
  completed_lessons: number
  certificates: number
}

export interface AdminTrack {
  id: string
  title: string
  difficulty: string
  estimated_hours: number
  is_active: boolean
  lessons: number
  completions: number
}

export interface AdminCertificate {
  id: string
  title: string
  user_name: string
  user_email: string
  issued_at: string
  validation_code: string
}
