import { apiGet } from "@/lib/api-client"
import type {
  RankingSummary,
  UserAchievement,
  UserBadge,
  UserCertificate,
} from "@/features/dashboard/types/gamification"

export function fetchMyBadges(): Promise<UserBadge[]> {
  return apiGet<UserBadge[]>("/gamification/me/badges")
}

export function fetchMyCertificates(): Promise<UserCertificate[]> {
  return apiGet<UserCertificate[]>("/gamification/me/certificates")
}

export function fetchRanking(): Promise<RankingSummary> {
  return apiGet<RankingSummary>("/gamification/ranking")
}

export function fetchMyAchievements(): Promise<UserAchievement[]> {
  return apiGet<UserAchievement[]>("/gamification/me/achievements")
}
