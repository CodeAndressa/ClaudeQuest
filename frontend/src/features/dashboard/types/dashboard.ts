export interface DashboardXp {
  total: number
  level: number
  xp_to_next_level: number
}

export interface DashboardStreak {
  current_days: number
  last_active_date: string | null
}

export interface DashboardRanking {
  position: number | null
  total_users: number
}

export interface DashboardNextLesson {
  track_id: string
  track_title: string
  lesson_title: string
  lesson_id: string
}

export interface DashboardSummary {
  xp: DashboardXp
  streak: DashboardStreak
  ranking: DashboardRanking
  next_lesson: DashboardNextLesson | null
  badges: unknown[]
  certificates: unknown[]
}
