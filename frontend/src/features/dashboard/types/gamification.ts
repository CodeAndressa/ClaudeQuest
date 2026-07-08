export interface Badge {
  id: string
  name: string
  description: string
  image: string | null
  category: "bronze" | "prata" | "ouro" | "platina" | "diamante" | "lendario"
}

export interface UserBadge {
  id: string
  badge_id: string
  earned_at: string
  badge: Badge
}

export interface UserCertificate {
  id: string
  certificate_id: string
  title: string
  hours: number
  validation_code: string
  issued_at: string
  pdf_url: string | null
}

export interface RankingUserEntry {
  user_id: string
  name: string
  score: number
  position: number
}

export interface RankingSummary {
  top: RankingUserEntry[]
  current_user: RankingUserEntry | null
  total_users: number
}

export type AchievementMetric =
  | "lessons_completed"
  | "streak_days"
  | "total_xp"
  | "badges_count"
  | "certificates_count"

export interface Achievement {
  id: string
  name: string
  description: string
  icon: string
  metric: AchievementMetric
  threshold: number
}

export interface UserAchievement {
  id: string
  achievement_id: string
  achieved_at: string
  achievement: Achievement
}
