import { apiDownload, apiGet } from "@/lib/api-client"
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

export function downloadCertificate(path: string): Promise<Blob> {
  return apiDownload(path.replace("/api/v1", ""))
}

export function fetchRanking(): Promise<RankingSummary> {
  return apiGet<RankingSummary>("/gamification/ranking")
}

export function fetchMyAchievements(): Promise<UserAchievement[]> {
  return apiGet<UserAchievement[]>("/gamification/me/achievements")
}
